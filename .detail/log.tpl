{% if output == ':github/pr' %}
**Heads up!** This is what the release notes will look like based on the notes.

{% endif %}
{% if not range %}
# Changelog
{% endif %}
{% for tag, notes_by_tag in notes.group('commit_tag').items() %}
## {{ tag|default('Unreleased', True) }} {% if tag.date %}({{ tag.date.date() }}){% endif %}

{% for type, notes_by_type in notes_by_tag.group('type', ascending_keys=True, none_key_last=True).items() %}
### {{ type|default('Other', True)|title }}
{% for note in notes_by_type %}

- {{ note.summary }} [{{ note.commit_author_name }}, {{ note.commit_sha[:7] }}]

{% if note.description %}
  {{ note.description|indent(2) }}
{% endif %}

{% endfor %}
{% endfor %}
{% endfor %}