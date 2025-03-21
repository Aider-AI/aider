---
nav_exclude: true
---

# Aider Documentation

Aider is AI pair programming in your terminal. This documentation will help you get the most out of aider.

<div class="toc">
{% assign pages_list = site.html_pages | sort: "nav_order" %}

<ul>
{% for page in pages_list %}
  {% if page.title and page.url != "/" and page.parent == nil and page.nav_exclude != true %}
    <li>
      <a href="{{ page.url | absolute_url }}">{{ page.title }}</a>{% if page.description %} <span style="font-size: 0.9em; font-style: italic;">— {{ page.description }}</span>{% endif %}
      
      {% assign children = site.html_pages | where: "parent", page.title | sort: "nav_order" %}
      {% if children.size > 0 %}
        <ul>
        {% for child in children %}
          {% if child.title %}
            <li>
              <a href="{{ child.url | absolute_url }}">{{ child.title }}</a>{% if child.description %} <span style="font-size: 0.9em; font-style: italic;">— {{ child.description }}</span>{% endif %}
              
              {% assign grandchildren = site.html_pages | where: "parent", child.title | sort: "nav_order" %}
              {% if grandchildren.size > 0 %}
                <ul>
                {% for grandchild in grandchildren %}
                  {% if grandchild.title %}
                    <li>
                      <a href="{{ grandchild.url | absolute_url }}">{{ grandchild.title }}</a>{% if grandchild.description %} <span style="font-size: 0.9em; font-style: italic;">— {{ grandchild.description }}</span>{% endif %}
                    </li>
                  {% endif %}
                {% endfor %}
                </ul>
              {% endif %}
            </li>
          {% endif %}
        {% endfor %}
        </ul>
      {% endif %}
    </li>
  {% endif %}
{% endfor %}
</ul>
</div>
