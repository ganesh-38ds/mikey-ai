import codecs
import re

with codecs.open('frontend/script.js', 'r', 'utf-8') as f:
    text = f.read()

text = text.replace(
    "travel: 'Suggest a short travel idea for a weekend escape.'\n      }",
    "travel: 'Suggest a short travel idea for a weekend escape.',\n        movies: 'What are the latest movie releases, or suggest a good sports movie.'\n      }"
)
text = text.replace(
    "topicLabels: ['Anime','Sports','Health','Study','Ideas','Motivation','Productivity','Tech','Travel'],",
    "topicLabels: ['Movies','Anime','Sports','Health','Study','Ideas','Motivation','Productivity','Tech','Travel'],",
    1
)
text = text.replace(
    "topicKeys: ['anime','sports','health','study','fun facts','motivation','productivity','tech','travel'],",
    "topicKeys: ['movies','anime','sports','health','study','fun facts','motivation','productivity','tech','travel'],",
    1
)

text = re.sub(
    r"(travel: '[^']+')(\n\s*\})",
    r"\1,\n        movies: '????? ???????? ???? ???????? ???????? ???? ?? ???? ?????????? ?????? ??????? ??????.'\2",
    text
)
text = re.sub(
    r"topicLabels: \['([^\]]+)'\],\s*topicKeys: \['anime'",
    r"topicLabels: ['????????','\1'],\n      topicKeys: ['anime'",
    text
)
text = re.sub(
    r"topicKeys: \['anime','sports','health','study','fun facts','motivation','productivity','tech','travel'\]",
    r"topicKeys: ['movies','anime','sports','health','study','fun facts','motivation','productivity','tech','travel']",
    text
)

with codecs.open('frontend/script.js', 'w', 'utf-8') as f:
    f.write(text)
print('Done')
