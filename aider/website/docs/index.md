---
layout: default
title: Home
nav_order: 1
permalink: /
---

# Aider Documentation

Aider is AI pair programming in your terminal. This documentation will help you get the most out of aider.

## Table of Contents

<div class="toc">
{% assign pages_list = site.html_pages | sort: "nav_order" %}

<ul>
{% for page in pages_list %}
  {% if page.title and page.url != "/" and page.parent == nil and page.nav_exclude != true %}
    <li>
      <a href="{{ page.url | absolute_url }}">{{ page.title }}</a>
      
      {% assign children = site.html_pages | where: "parent", page.title | sort: "nav_order" %}
      {% if children.size > 0 %}
        <ul>
        {% for child in children %}
          {% if child.title %}
            <li>
              <a href="{{ child.url | absolute_url }}">{{ child.title }}</a>
              
              {% assign grandchildren = site.html_pages | where: "parent", child.title | sort: "nav_order" %}
              {% if grandchildren.size > 0 %}
                <ul>
                {% for grandchild in grandchildren %}
                  {% if grandchild.title %}
                    <li>
                      <a href="{{ grandchild.url | absolute_url }}">{{ grandchild.title }}</a>
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

## Quick Links

- [Installation Guide](/docs/installation)
- [Getting Started](/docs/getting-started)
- [Command Reference](/docs/commands)
- [Configuration Options](/docs/configuration)

## About Aider

Aider is an open-source tool that brings the power of AI coding assistants directly to your terminal. Use natural language to add features, fix bugs, and refactor code with an AI assistant that understands your entire codebase.
