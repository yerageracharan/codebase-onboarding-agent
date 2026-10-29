"""Create screenshot-style SVG captures from real CLI stdout and generated report text.

No screenshot is filled with invented terminal output: each terminal panel reads a
saved stdout/stderr capture produced by verification-demo.yml. Report panels are
excerpted from the report written by the actual CLI invocation.
"""
from __future__ import annotations

import html
import os
import textwrap
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
U‘T’Q–HH“ÓÕÈ™^[\\ÈˆÈ™\šYšXØ][Ûˆ‚”ÒÕÑTˆH‘T’Q–HÈœØÜ™Y[œÚİÈ‚‚‚™Yˆ™XYØØ\\™J˜[YNˆİŠHOˆİ‚ˆ]H‘T’Q–HÈ˜[YBˆ™]\›ˆ]œ™XYİ^
[˜ÛÙ[™ÏH]‹N‹\œ›ÜœÏHœ™\XÙHŠKœİš\
—ˆŠHYˆ]™^\İÊ
H[ÙHˆØ\\™H›İ›ÙXÙYˆÛ˜[Y_H‚‚‚™YˆÜ˜\
[™\Îˆ\İÜİ—KÚYˆ[HLÊHOˆ\İÜİ—N‚ˆİ]ˆ\İÜİ—HH×Bˆ›Üˆ[™H[ˆ[™\Î‚ˆYˆ›İ[™N‚ˆİ]˜\[™
ˆŠBˆÛÛ[YBˆÜ˜\YH^Ü˜\Ü˜\
[™KÚY]ÚYİXœÙ\]Y[Ú[™[Hˆ‹œ™XZ×ÛÛ™×İÛÜ™ÏUYKœ™XZ×ÛÛ—Ú\[œÏQ˜[ÙJBˆİ]™^[™
Ü˜\YÜˆÈˆ—JBˆ™]\›ˆİ]‚‚™Yˆ\›Z[˜[Üİ™Ê]Nˆİ‹ÛÛ[X[™ˆİ‹ÛÛ[ˆİ‹š[[˜[YNˆİ‹
‹X^Û[™\Îˆ[HÍ
HOˆ›Û™N‚ˆ[™\ÈHÜ˜\
ÛÛ[œÜ][™\Ê
KLŠBˆÛZ]YHX^
[Š[™\ÊHHX^Û[™\ÊBˆÚİÛˆH[™\ÖÎ›X^Û[™\×BˆYˆÛZ]Y‚ˆÚİÛ–ËLN—HHÙˆ¸ )ˆÛÛZ]YHY][Û˜[Ø\\™Y[™\ÈÛZ]Yœ›ÛH\ÈØÜ™Y[œÚİˆBˆ[™WÚHÂˆZYÚHML
ÈX^
K[ŠÚİÛŠJH
ˆ[™WÚ
Èˆ›ÙHH×Bˆ›ÜˆK[™H[ˆ[[Y\˜]JÚİÛŠN‚ˆ›ÙK˜\[™
‰Ï^HˆˆOHÌLH
ÈH
ˆ[™WÚHˆÛ\ÜÏH\›HÚ[™\ØØ\J[™J_Oİ^‰ÊBˆİ™ÈH‰ÉÈ	