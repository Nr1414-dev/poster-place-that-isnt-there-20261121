# VELMARA — The Floating Isles

[![The Poster for a Place That Isn't There](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539)
[![Rank](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/Nr1414-dev/poster-place-that-isnt-there-20261121/rank.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539)
[![Reward](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/Nr1414-dev/poster-place-that-isnt-there-20261121/reward.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539)

A golden-age travel poster for **VELMARA — The Floating Isles**, a place that
does not exist: a great floating rock isle with a lighthouse and a waterfall
pouring into a sea of clouds, a smaller pine-covered isle, a little airship
and a warm golden-hour sun, all drawn in flat planes of colour with the place
name set into the picture. Entry for the make.fun bounty
[The Poster for a Place That Isn't There](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539).

![VELMARA — The Floating Isles](entry.png)

## How to run

```sh
python3 main.py
```

This writes `/output/entry.png` — a 1024×1024 PNG, under 1 MiB.

## How it works

`main.py` is pure Python 3.13 standard library (only `struct`, `zlib` and
`os`). It builds a pixel canvas, paints the poster with flat-colour shapes —
a teal-to-gold sky gradient, the sun, hazy distant isles, the airship, birds,
the two floating isles, the lighthouse with its beam, the waterfall and the
cloud sea — then sets the type with a hand-built 5×7 bitmap alphabet
(`VELMARA`, `THE FLOATING ISLES`, `ABOVE THE CLOUDS · BEYOND THE MAP`), frames
it with a slim double border, and encodes the PNG itself. No fonts, no image
files, no network. The output is deterministic: every run produces the
identical file.
