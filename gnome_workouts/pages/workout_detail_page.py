from __future__ import annotations

from dataclasses import dataclass, field

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")

from gi.repository import Adw, GObject, Gtk

from ..models import SetPlan
from ..ui_utils import *


@dataclass
class _ExerciseForm:
    form: Gtk.Box
    name_row: Adw.EntryRow
    type_dd: Gtk.DropDown
    rest_adj: Gtk.Adjustment
    sets_adj: Gtk.Adjustment
    dur_adj: Gtk.Adjustment
    set_adjs: list[tuple[Gtk.Adjustment, Gtk.Adjustment]] = field(default_factory=list)


class WorkoutDetailPage(Adw.NavigationPage):
    __gtype_name__ = "GnomeWorkoutsWorkoutDetailPage"

    __gsignals__ = {
        "begin-workout": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
    }

    def __init__(self, app: Adw.Application, workout_id: int) -> None:
        super().__init__(title="Workout")
        self._app = app
        self._workout_id = workout_id

        header = Adw.HeaderBar()

        add_btn = create_header_button(
            "list-add-symbolic",
            tooltip="Add an exercise to this workout",
            accessible_name="Add Exercise",
        )
        add_btn.connect("clicked", self._on_add_exercise_clicked)
        header.pack_start(add_btn)

        self._body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        set_margins(self._body, all=18)

        clamp = Adw.Clamp(maximum_size=760, tightening_threshold=760)
        clamp.set_hexpand(True)
        clamp.set_vexpand(True)
        clamp.set_child(self._body)

        self._empty_page = Adw.StatusPage(
            title="No Exercises Yet",
            description="Add your first exercise using the \u201c+\u201d button above.",
            icon_name="view-list-symbolic",
        )

        self._exercises_stack = Gtk.Stack()
        self._exercises_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._exercises_stack.set_vexpand(True)
        self._exercises_stack.add_named(clamp, "list")
        self._exercises_stack.add_named(self._empty_page, "empty")

        self._toast_overlay = Adw.ToastOverlay()
        self._toast_overlay.set_child(self._exercises_stack)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(self._toast_overlay)
        self.set_child(toolbar)

        self._reload()

    @property
    def _db(self):
        return self._app.db

    def _show_error(self, message: str) -> None:
        self._toast_overlay.add_toast(Adw.Toast(title=message))

    def _reload(self) -> None:
        clear_container(self._body)
        plan = self._db.get_workout_plan(self._workout_id)
        if plan is None:
            self.set_title("Workout")
            label = Gtk.Label(label="This workout could not be loaded.")
            label.add_css_class("dim-label")
            self._body.append(label)
            return

        self._plan = plan
        self.set_title(plan.workout.name)

        if not plan.exercises:
            self._exercises_stack.set_visible_child_name("empty")
            return

        self._exercises_stack.set_visible_child_name("list")
        prefs = self._app.prefs
        total = len(plan.exercises)

        list_box = create_boxed_listbox()

        for i, ex in enumerate(plan.exercises):
            row = Adw.ActionRow(title=ex.name)
            sets = plan.sets_by_exercise_id.get(ex.id, [])

            row.set_activatable(True)
            row.connect(
                "activated", lambda _r, eid=ex.id: self._open_edit_exercise_dialog(eid)
            )

            if total > 1:
                up_btn = Gtk.Button()
                up_btn.set_icon_name("go-up-symbolic")
                up_btn.set_valign(Gtk.Align.CENTER)
                up_btn.set_sensitive(i > 0)
                if i > 0:
                    prev_id = plan.exercises[i - 1].id
                    up_btn.connect(
                        "clicked",
                        lambda _b, a=ex.id, b=prev_id: self._move_exercise(a, b),
                    )
                style_header_icon_button(
                    up_btn, tooltip="Move up", accessible_name=f"Move {ex.name} up"
                )
                row.add_suffix(up_btn)

                down_btn = Gtk.Button()
                down_btn.set_icon_name("go-down-symbolic")
                down_btn.set_valign(Gtk.Align.CENTER)
                down_btn.set_sensitive(i < total - 1)
                if i < total - 1:
                    next_id = plan.exercises[i + 1].id
                    down_btn.connect(
                        "clicked",
                        lambda _b, a=ex.id, b=next_id: self._move_exercise(a, b),
                    )
                style_header_icon_button(
                    down_btn,
                    tooltip="Move down",
                    accessible_name=f"Move {ex.name} down",
                )
                row.add_suffix(down_btn)

            del_btn = Gtk.Button()
            del_btn.set_icon_name("user-trash-symbolic")
            del_btn.set_valign(Gtk.Align.CENTER)
            del_btn.connect(
                "clicked", lambda _b, eid=ex.id: self._on_remove_exercise_clicked(eid)
            )
            style_header_icon_button(
                del_btn,
                tooltip=f"Remove \u201c{ex.name}\u201d from this workout",
                accessible_name=f"Remove {ex.name}",
            )
            row.add_suffix(del_btn)

            if ex.exercise_type == "timed" and ex.timed_seconds is not None:
                parts = [
                    f"{len(sets)} set(s)",
                    f"{ex.timed_seconds}s hold",
                    f"rest {ex.rest_seconds}s",
                ]
            else:
                parts = [f"{len(sets)} set(s)"]
                reps_vals = [s.target_reps for s in sets if s.target_reps is not None]
                kg_vals = [
                    s.target_weight_kg
                    for s in sets
                    if s.target_weight_kg is not None and s.target_weight_kg > 0
                ]
                if reps_vals:
                    if len(set(reps_vals)) == 1:
                        parts.append(f"{reps_vals[0]} reps")
                    else:
                        parts.append(f"{min(reps_vals)}\u2013{max(reps_vals)} reps")
                if kg_vals:
                    if len(set(kg_vals)) == 1:
                        parts.append(
                            f"{prefs.kg_to_display(kg_vals[0]):g} {prefs.weight_label}"
                        )
                    else:
                        lo = prefs.kg_to_display(min(kg_vals))
                        hi = prefs.kg_to_display(max(kg_vals))
                        parts.append(f"{lo:g}\u2013{hi:g} {prefs.weight_label}")
                parts.append(f"rest {ex.rest_seconds}s")
            if ex.superset_group is not None:
                partner = next(
                    (
                        e
                        for e in plan.exercises
                        if e.id != ex.id and e.superset_group == ex.superset_group
                    ),
                    None,
                )
                if partner is not None:
                    parts.append(f"superset with {partner.name}")
            row.set_subtitle(" \u2022 ".join(parts))

            row.set_subtitle_lines(2)
            list_box.append(row)

        self._body.append(list_box)

        begin_btn = Gtk.Button(label="Begin Workout")
        begin_btn.add_css_class("suggested-action")
        begin_btn.connect("clicked", self._on_begin_clicked)
        begin_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        begin_row.set_halign(Gtk.Align.CENTER)
        set_margins(begin_row, top=12)
        begin_row.append(begin_btn)
        self._body.append(begin_row)

    # for building forms

    def _build_exercise_form(
        self,
        *,
        name: str = "",
        exercise_type: str = "reps",
        rest_seconds: int = 90,
        initial_sets: list[SetPlan] | None = None,
        timed_seconds: int = 45,
    ) -> _ExerciseForm:
        prefs = self._app.prefs

        if initial_sets:
            init: list[tuple[int, float]] = [
                (
                    s.target_reps if s.target_reps is not None else 10,
                    prefs.kg_to_display(s.target_weight_kg)
                    if s.target_weight_kg is not None
                    else 0.0,
                )
                for s in initial_sets
            ]
        else:
            init = [(10, 0.0), (10, 0.0), (10, 0.0)]

        name_row = Adw.EntryRow(title="Name")
        name_row.set_text(name)

        type_model = Gtk.StringList()
        type_model.append("Reps")
        type_model.append("Timed")
        type_dd = Gtk.DropDown(model=type_model)
        type_dd.set_selected(0 if exercise_type == "reps" else 1)
        type_dd.set_hexpand(True)
        type_dd.set_valign(Gtk.Align.CENTER)
        set_accessible_label(type_dd, "Exercise type")
        type_row = Adw.ActionRow(title="Exercise Type")
        type_row.add_suffix(type_dd)

        rest_adj = Gtk.Adjustment(
            value=rest_seconds, lower=0, upper=600, step_increment=5
        )
        rest_row = Adw.SpinRow(
            title="Rest Between Sets (seconds)", adjustment=rest_adj, digits=0
        )

        sets_adj = Gtk.Adjustment(value=len(init), lower=1, upper=20, step_increment=1)
        sets_row = Adw.SpinRow(title="Number of Sets", adjustment=sets_adj, digits=0)

        dur_adj = Gtk.Adjustment(
            value=timed_seconds, lower=1, upper=600, step_increment=1
        )
        timed_row = Adw.SpinRow(
            title="Hold Duration (seconds)", adjustment=dur_adj, digits=0
        )

        set_adjs: list[tuple[Gtk.Adjustment, Gtk.Adjustment]] = []
        sets_rows_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        _sync_sids: list[tuple[Gtk.Adjustment, int]] = []

        def _propagate_first(*_args: object) -> None:
            if not set_adjs:
                return
            r0, w0 = set_adjs[0]
            for r_adj, w_adj in set_adjs[1:]:
                r_adj.set_value(r0.get_value())
                w_adj.set_value(w0.get_value())

        def _set_rows_sensitive(sensitive: bool) -> None:
            child = sets_rows_box.get_first_child()
            idx = 0
            while child is not None:
                if idx > 0:
                    child.set_sensitive(sensitive)
                idx += 1
                child = child.get_next_sibling()

        def _on_sync_toggled(*_args: object) -> None:
            if sync_row.get_active():
                _propagate_first()
                if set_adjs:
                    r0, w0 = set_adjs[0]
                    _sync_sids.append(
                        (r0, r0.connect("value-changed", _propagate_first))
                    )
                    _sync_sids.append(
                        (w0, w0.connect("value-changed", _propagate_first))
                    )
                _set_rows_sensitive(False)
            else:
                for adj, sid in _sync_sids:
                    adj.disconnect(sid)
                _sync_sids.clear()
                _set_rows_sensitive(True)

        all_same = len(init) <= 1 or all(
            r == init[0][0] and w == init[0][1] for r, w in init[1:]
        )
        sync_row = Adw.SwitchRow(title="Same for All Sets")
        sync_row.set_active(all_same)
        sync_row.connect("notify::active", _on_sync_toggled)

        def _add_set_row(reps: int = 10, weight: float = 0.0) -> None:
            n = len(set_adjs) + 1
            r_adj = Gtk.Adjustment(value=reps, lower=0, upper=999, step_increment=1)
            w_adj = Gtk.Adjustment(
                value=weight,
                lower=0.0,
                upper=prefs.weight_max,
                step_increment=prefs.weight_step,
            )
            set_adjs.append((r_adj, w_adj))

            row = Adw.ActionRow(title=f"Set {n}")
            if n > 1 and sync_row.get_active():
                row.set_sensitive(False)

            r_spin = Gtk.SpinButton(adjustment=r_adj, digits=0)
            r_spin.set_valign(Gtk.Align.CENTER)
            r_spin.set_max_width_chars(4)
            r_label = Gtk.Label(label=" reps")
            r_label.add_css_class("dim-label")
            r_label.set_valign(Gtk.Align.CENTER)

            w_spin = Gtk.SpinButton(adjustment=w_adj, digits=1)
            w_spin.set_valign(Gtk.Align.CENTER)
            w_spin.set_max_width_chars(5)
            w_label = Gtk.Label(label=f" {prefs.weight_label}")
            w_label.add_css_class("dim-label")
            w_label.set_valign(Gtk.Align.CENTER)

            suffix_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            suffix_box.set_valign(Gtk.Align.CENTER)
            for w in (r_spin, r_label, w_spin, w_label):
                suffix_box.append(w)
            row.add_suffix(suffix_box)
            sets_rows_box.append(row)

        def _remove_last_set_row() -> None:
            if set_adjs:
                set_adjs.pop()
                child = sets_rows_box.get_last_child()
                if child is not None:
                    sets_rows_box.remove(child)

        for reps, weight in init:
            _add_set_row(reps, weight)

        _on_sync_toggled()

        def _on_sets_count_changed(*_args: object) -> None:
            target = int(sets_adj.get_value())
            while len(set_adjs) < target:
                last_r, last_w = set_adjs[-1] if set_adjs else (None, None)
                _add_set_row(
                    int(last_r.get_value()) if last_r else 10,
                    float(last_w.get_value()) if last_w else 0.0,
                )
            while len(set_adjs) > target:
                _remove_last_set_row()

        sets_adj.connect("value-changed", _on_sets_count_changed)

        form = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        for widget in (
            name_row,
            type_row,
            rest_row,
            sets_row,
            sync_row,
            sets_rows_box,
            timed_row,
        ):
            form.append(widget)

        def _sync_type(*_args: object) -> None:
            is_reps = type_dd.get_selected() == 0
            sync_row.set_visible(is_reps)
            sets_rows_box.set_visible(is_reps)
            timed_row.set_visible(not is_reps)

        type_dd.connect("notify::selected", _sync_type)
        _sync_type()

        return _ExerciseForm(
            form=form,
            name_row=name_row,
            type_dd=type_dd,
            rest_adj=rest_adj,
            sets_adj=sets_adj,
            dur_adj=dur_adj,
            set_adjs=set_adjs,
        )

    # handling

    def _on_begin_clicked(self, _btn: Gtk.Button) -> None:
        self.emit("begin-workout", int(self._workout_id))

    def _move_exercise(self, exercise_id_a: int, exercise_id_b: int) -> None:
        try:
            self._db.swap_exercise_order(self._workout_id, exercise_id_a, exercise_id_b)
        except ValueError as exc:
            self._show_error(str(exc))
            return
        self._reload()

    def _on_remove_exercise_clicked(self, exercise_id: int) -> None:
        dialog = Adw.AlertDialog()
        dialog.set_heading("Remove Exercise?")
        dialog.set_body(
            "This cannot be undone. Planned sets for this exercise will be removed from the workout."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Remove")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")

        def on_response(_d: Adw.AlertDialog, response: str) -> None:
            if response != "delete":
                return
            try:
                self._db.delete_exercise_from_workout(self._workout_id, exercise_id)
            except ValueError as exc:
                self._show_error(str(exc))
                return
            self._reload()

        dialog.connect("response", on_response)
        present_dialog(dialog, self)

    def _open_edit_exercise_dialog(self, exercise_id: int) -> None:
        details = self._db.get_exercise_details(exercise_id)
        if details is None:
            return
        exercise, sets = details
        prefs = self._app.prefs

        f = self._build_exercise_form(
            name=exercise.name,
            exercise_type=exercise.exercise_type,
            rest_seconds=exercise.rest_seconds,
            initial_sets=sets,
            timed_seconds=exercise.timed_seconds
            if exercise.timed_seconds is not None
            else 45,
        )

        other_exercises = [ex for ex in self._plan.exercises if ex.id != exercise_id]
        partner_ids: list[int | None] = [None]
        superset_model = Gtk.StringList()
        superset_model.append("None")
        current_group = exercise.superset_group
        current_partner_idx = 0
        for i, other in enumerate(other_exercises):
            superset_model.append(other.name)
            partner_ids.append(other.id)
            if current_group is not None and other.superset_group == current_group:
                current_partner_idx = i + 1

        superset_dd: Gtk.DropDown | None = None
        if other_exercises:
            superset_dd = Gtk.DropDown(model=superset_model)
            superset_dd.set_selected(current_partner_idx)
            superset_dd.set_hexpand(True)
            superset_dd.set_valign(Gtk.Align.CENTER)
            set_accessible_label(superset_dd, "Superset partner exercise")
            ss_row = Adw.ActionRow(title="Superset With")
            ss_row.set_subtitle("Run back-to-back with no rest in between")
            ss_row.set_subtitle_lines(2)
            ss_row.add_suffix(superset_dd)
            f.form.append(ss_row)

        dialog = Adw.AlertDialog()
        dialog.set_heading("Edit Exercise")
        dialog.set_extra_child(f.form)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("save", "Save")
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("save")
        dialog.set_close_response("cancel")
        dialog.set_response_enabled("save", bool(exercise.name.strip()))
        f.name_row.connect(
            "changed",
            lambda _r: dialog.set_response_enabled(
                "save", bool(f.name_row.get_text().strip())
            ),
        )

        def on_response(_d: Adw.AlertDialog, response: str) -> None:
            if response != "save":
                return
            typ = "reps" if f.type_dd.get_selected() == 0 else "timed"
            if typ == "reps":
                set_configs: list[tuple[int | None, float | None]] = [
                    (
                        int(r_adj.get_value()),
                        prefs.display_to_kg(float(w_adj.get_value()))
                        if float(w_adj.get_value()) > 0
                        else None,
                    )
                    for r_adj, w_adj in f.set_adjs
                ]
            else:
                set_configs = [(None, None)] * int(f.sets_adj.get_value())
            try:
                self._db.update_exercise(
                    exercise_id,
                    name=f.name_row.get_text().strip(),
                    exercise_type=typ,
                    rest_seconds=int(f.rest_adj.get_value()),
                    timed_seconds=int(f.dur_adj.get_value())
                    if typ == "timed"
                    else None,
                    set_configs=set_configs,
                )
            except ValueError as exc:
                self._show_error(str(exc))
                return

            if superset_dd is not None:
                new_idx = superset_dd.get_selected()
                new_partner_id = (
                    partner_ids[new_idx] if new_idx < len(partner_ids) else None
                )
                old_partner_id = (
                    partner_ids[current_partner_idx]
                    if current_partner_idx < len(partner_ids)
                    else None
                )
                if new_partner_id != old_partner_id:
                    if current_group is not None:
                        self._db.unlink_exercise_from_superset(
                            self._workout_id, exercise_id
                        )
                    if new_partner_id is not None:
                        new_partner_ex = next(
                            (
                                ex
                                for ex in self._plan.exercises
                                if ex.id == new_partner_id
                            ),
                            None,
                        )
                        if new_partner_ex and new_partner_ex.superset_group is not None:
                            self._db.unlink_exercise_from_superset(
                                self._workout_id, new_partner_id
                            )
                        self._db.set_exercises_as_superset(
                            self._workout_id, exercise_id, new_partner_id
                        )

            self._reload()

        dialog.connect("response", on_response)
        present_dialog(dialog, self)

    def _on_add_exercise_clicked(self, _btn: Gtk.Button) -> None:
        prefs = self._app.prefs
        f = self._build_exercise_form()

        dialog = Adw.AlertDialog()
        dialog.set_heading("Add Exercise")
        dialog.set_extra_child(f.form)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("add", "Add Exercise")
        dialog.set_response_appearance("add", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("add")
        dialog.set_close_response("cancel")
        dialog.set_response_enabled("add", False)
        f.name_row.connect(
            "changed",
            lambda _r: dialog.set_response_enabled(
                "add", bool(f.name_row.get_text().strip())
            ),
        )

        def on_response(_d: Adw.AlertDialog, response: str) -> None:
            if response != "add":
                return
            typ = "reps" if f.type_dd.get_selected() == 0 else "timed"
            if typ == "reps":
                set_configs: list[tuple[int | None, float | None]] = [
                    (
                        int(r_adj.get_value()),
                        prefs.display_to_kg(float(w_adj.get_value()))
                        if float(w_adj.get_value()) > 0
                        else None,
                    )
                    for r_adj, w_adj in f.set_adjs
                ]
            else:
                set_configs = [(None, None)] * int(f.sets_adj.get_value())
            try:
                self._db.add_exercise_to_workout(
                    self._workout_id,
                    name=f.name_row.get_text().strip(),
                    exercise_type=typ,
                    rest_seconds=int(f.rest_adj.get_value()),
                    timed_seconds=int(f.dur_adj.get_value())
                    if typ == "timed"
                    else None,
                    set_configs=set_configs,
                )
            except ValueError as exc:
                self._show_error(str(exc))
                return
            self._reload()

        dialog.connect("response", on_response)
        present_dialog(dialog, self)
