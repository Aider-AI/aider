---
nav_order: 50
---
# Supported languages

Aider will work with most every popular code language,
because the leading LLMs know most of them.
Even if your language isn't listed below, aider may still be effective for you.
The best thing to do is try!

Aider uses a [map of your entire git repo](https://aider.chat/docs/repomap.html),
which helps it work well in larger codebases.
Aider uses tree-sitter to understand the language listed below,
and can analyze them when creating the repo map.

<table>
<tr>
  <th>
    Language
  </th>
  <th>
    File extension
  </th>
</tr>
<!--[[[cog
from aider.repomap import get_supported_languages_md
cog.out(get_supported_languages_md())
]]]-->
<tr><td style="text-align: center;">bash                </td>
<td style="text-align: center;">.bash               </td>
</tr><tr><td style="text-align: center;">c                   </td>
<td style="text-align: center;">.c                  </td>
</tr><tr><td style="text-align: center;">c_sharp             </td>
<td style="text-align: center;">.cs                 </td>
</tr><tr><td style="text-align: center;">commonlisp          </td>
<td style="text-align: center;">.cl                 </td>
</tr><tr><td style="text-align: center;">cpp                 </td>
<td style="text-align: center;">.cc                 </td>
</tr><tr><td style="text-align: center;">cpp                 </td>
<td style="text-align: center;">.cpp                </td>
</tr><tr><td style="text-align: center;">css                 </td>
<td style="text-align: center;">.css                </td>
</tr><tr><td style="text-align: center;">dockerfile          </td>
<td style="text-align: center;">.dockerfile         </td>
</tr><tr><td style="text-align: center;">dot                 </td>
<td style="text-align: center;">.dot                </td>
</tr><tr><td style="text-align: center;">elisp               </td>
<td style="text-align: center;">.el                 </td>
</tr><tr><td style="text-align: center;">elixir              </td>
<td style="text-align: center;">.ex                 </td>
</tr><tr><td style="text-align: center;">elm                 </td>
<td style="text-align: center;">.elm                </td>
</tr><tr><td style="text-align: center;">embedded_template   </td>
<td style="text-align: center;">.et                 </td>
</tr><tr><td style="text-align: center;">erlang              </td>
<td style="text-align: center;">.erl                </td>
</tr><tr><td style="text-align: center;">go                  </td>
<td style="text-align: center;">.go                 </td>
</tr><tr><td style="text-align: center;">gomod               </td>
<td style="text-align: center;">.gomod              </td>
</tr><tr><td style="text-align: center;">hack                </td>
<td style="text-align: center;">.hack               </td>
</tr><tr><td style="text-align: center;">haskell             </td>
<td style="text-align: center;">.hs                 </td>
</tr><tr><td style="text-align: center;">hcl                 </td>
<td style="text-align: center;">.hcl                </td>
</tr><tr><td style="text-align: center;">html                </td>
<td style="text-align: center;">.html               </td>
</tr><tr><td style="text-align: center;">java                </td>
<td style="text-align: center;">.java               </td>
</tr><tr><td style="text-align: center;">javascript          </td>
<td style="text-align: center;">.js                 </td>
</tr><tr><td style="text-align: center;">javascript          </td>
<td style="text-align: center;">.mjs                </td>
</tr><tr><td style="text-align: center;">jsdoc               </td>
<td style="text-align: center;">.jsdoc              </td>
</tr><tr><td style="text-align: center;">json                </td>
<td style="text-align: center;">.json               </td>
</tr><tr><td style="text-align: center;">julia               </td>
<td style="text-align: center;">.jl                 </td>
</tr><tr><td style="text-align: center;">kotlin              </td>
<td style="text-align: center;">.kt                 </td>
</tr><tr><td style="text-align: center;">lua                 </td>
<td style="text-align: center;">.lua                </td>
</tr><tr><td style="text-align: center;">make                </td>
<td style="text-align: center;">.mk                 </td>
</tr><tr><td style="text-align: center;">objc                </td>
<td style="text-align: center;">.m                  </td>
</tr><tr><td style="text-align: center;">ocaml               </td>
<td style="text-align: center;">.ml                 </td>
</tr><tr><td style="text-align: center;">perl                </td>
<td style="text-align: center;">.pl                 </td>
</tr><tr><td style="text-align: center;">php                 </td>
<td style="text-align: center;">.php                </td>
</tr><tr><td style="text-align: center;">python              </td>
<td style="text-align: center;">.py                 </td>
</tr><tr><td style="text-align: center;">ql                  </td>
<td style="text-align: center;">.ql                 </td>
</tr><tr><td style="text-align: center;">r                   </td>
<td style="text-align: center;">.R                  </td>
</tr><tr><td style="text-align: center;">r                   </td>
<td style="text-align: center;">.r                  </td>
</tr><tr><td style="text-align: center;">regex               </td>
<td style="text-align: center;">.regex              </td>
</tr><tr><td style="text-align: center;">rst                 </td>
<td style="text-align: center;">.rst                </td>
</tr><tr><td style="text-align: center;">ruby                </td>
<td style="text-align: center;">.rb                 </td>
</tr><tr><td style="text-align: center;">rust                </td>
<td style="text-align: center;">.rs                 </td>
</tr><tr><td style="text-align: center;">scala               </td>
<td style="text-align: center;">.scala              </td>
</tr><tr><td style="text-align: center;">sql                 </td>
<td style="text-align: center;">.sql                </td>
</tr><tr><td style="text-align: center;">sqlite              </td>
<td style="text-align: center;">.sqlite             </td>
</tr><tr><td style="text-align: center;">toml                </td>
<td style="text-align: center;">.toml               </td>
</tr><tr><td style="text-align: center;">tsq                 </td>
<td style="text-align: center;">.tsq                </td>
</tr><tr><td style="text-align: center;">typescript          </td>
<td style="text-align: center;">.ts                 </td>
</tr><tr><td style="text-align: center;">typescript          </td>
<td style="text-align: center;">.tsx                </td>
</tr><tr><td style="text-align: center;">yaml                </td>
<td style="text-align: center;">.yaml               </td>
</tr>
<!--[[[end]]]-->

</table>
