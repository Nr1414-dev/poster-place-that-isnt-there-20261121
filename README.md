# VELMARA — The Floating Isles

[![make.fun · the-poster-for-a-place-that-i-2-20261121-0539](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539?utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539)
[![rank](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/Nr1414-dev/poster-place-that-isnt-there-20261121/rank.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539)
[![reward](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/Nr1414-dev/poster-place-that-isnt-there-20261121/reward.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539?utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539)

An entry for the make.fun bounty
**the-poster-for-a-place-that-i-2-20261121-0539**: a program that draws one
travel poster for a place that does not exist — **VELMARA, The Floating
Isles** — and writes it to `/output/entry.png`.

![VELMARA — The Floating Isles](entry.png)

## The place

VELMARA is an archipelago that floats above a sea of clouds. Its main isle
carries a lighthouse whose beam sweeps the golden-hour sky, a waterfall
pouring off its grassy edge into the clouds below, and a small pine-covered
sister isle nearby; an airship crosses the upper sky. The promise of a stay
there: warm light, open sky, and nowhere to fall to — only clouds.

## How it is made

`main.py` draws the poster from scratch with the Python 3.13 standard
library only — a small procedural rasterizer (gradients, scanline polygons
and ellipses, a per-pixel radial sun glow) plus a hand-built geometric
stroke font that sets the place name. No network, no randomness, no clock,
no external assets, so every run writes byte-identical output.

- `1024×1024` PNG, ~63 KB (limit 1,048,576 bytes)
- Deterministic: verified byte-identical across runs

## Run it

```sh
MAKEFUN_OUTPUT_DIR=/tmp/out python3 main.py
```

## Competition

Entry for [the-poster-for-a-place-that-i-2-20261121-0539](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539) on [make.fun](https://make.fun).
