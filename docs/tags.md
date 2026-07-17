---
layout: page
title: 태그
permalink: /tags/
---

실험을 태그로 묶어서 훑어보는 페이지. 새 글이 올라올 때마다 자동으로 갱신됨.

{% for tag in site.tags %}
## {{ tag[0] }}

{% for post in tag[1] %}- [{{ post.title }}]({{ post.url | relative_url }}) — {{ post.date | date: "%Y-%m-%d" }}
{% endfor %}
{% endfor %}
