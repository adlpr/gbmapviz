# gbmapviz

Script to generate visually navigable HTML from the mapfile produced by [RGBDS](https://github.com/rednex/rgbds) linker `rgblink`.

Requires Python 3.6+ and [Jinja2](http://jinja.pocoo.org/docs/2.10/).

Call at the end of your assembly script for a handy visual debugging aid.

## Usage

```
python gbmapviz.py [-h] [-w] inf_name

positional arguments:
  inf_name    input filename (with or without .asm extension)

optional arguments:
  -h, --help  show this help message and exit
  -w          single WRAM bank mode (see rgblink -w)
```

* read: `mapfilename.map`
* output: `mapfilename.map.html`
