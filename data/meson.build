desktop_file = install_data(
  'io.github.AronCalvert.Workouts.desktop.in',
  rename: 'io.github.AronCalvert.Workouts.desktop',
  install_dir: get_option('datadir') / 'applications',
)

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils,
    args: [get_option('datadir') / 'applications' / 'io.github.AronCalvert.Workouts.desktop'],
  )
endif

install_data(
  'icons/hicolor/scalable/apps/io.github.AronCalvert.Workouts.svg',
  install_dir: get_option('datadir') / 'icons/hicolor/scalable/apps',
)

install_data(
  'icons/hicolor/symbolic/apps/io.github.AronCalvert.Workouts-symbolic.svg',
  install_dir: get_option('datadir') / 'icons/hicolor/symbolic/apps',
)

metainfo_file = install_data(
  'io.github.AronCalvert.Workouts.metainfo.xml.in',
  rename: 'io.github.AronCalvert.Workouts.metainfo.xml',
  install_dir: get_option('datadir') / 'metainfo',
)

install_data(
  'screenshots/main-window.png',
  'screenshots/workout-detail.png',
  'screenshots/workout-run.png',
  'screenshots/rest-timer.png',
  'screenshots/workout-complete.png',
  'screenshots/history.png',
  install_dir: get_option('datadir') / 'metainfo/screenshots',
)

appstream_util = find_program('appstream-util', required: false)
if appstream_util.found()
  test('Validate metainfo file', appstream_util,
    args: ['validate', get_option('datadir') / 'metainfo' / 'io.github.AronCalvert.Workouts.metainfo.xml'],
  )
endif

install_data(
  'io.github.AronCalvert.Workouts.gschema.xml',
  install_dir: get_option('datadir') / 'glib-2.0/schemas',
)
