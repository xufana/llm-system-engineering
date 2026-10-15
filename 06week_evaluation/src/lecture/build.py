import pathlib
p=pathlib.Path(__file__).parent
css=(p/'base.css').read_text()+(p/'extra.css').read_text()
head='<title>Как понять, что это работает, и работает хорошо?</title>\n<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Serif:wght@600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">\n<style>'+css+'</style>\n'
body=(p/'body.html').read_text(); js='<script>\n'+(p/'app.js').read_text()+'</script>\n'
(p/'artifact.html').write_text(head+body+js)
(p.parent.parent/'lecture7_evaluation.html').write_text('<!doctype html>\n<html lang="ru">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'+head+'</head>\n<body>\n'+body+js+'</body>\n</html>\n')
print('ok')
