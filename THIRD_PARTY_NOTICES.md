# Data sources and attribution

## Earthquake catalogue

The supplied USGS FDSN earthquake catalogue covers 1965–2025 and reported magnitude ≥5.5. Source: [USGS earthquake catalogue service](https://earthquake.usgs.gov/fdsnws/event/1/).

The exact raw snapshot is identified by `data/processed/revised/reproduction_manifest.json`. Its retrieval date was not recorded. The supplied catalogue contains 28,557 events, one fewer than the originally reported run; the discrepancy cannot be reconstructed from the original summaries. No replacement download is needed to run the app or notebook.

## Tectonic plate boundaries

`data/external/plate_boundaries_pb2002.json` comes from the [fraxen/tectonicplates collection](https://github.com/fraxen/tectonicplates), based on Peter Bird's *An updated digital model of plate boundaries* (2003), DOI [10.1029/2001GC000252](https://doi.org/10.1029/2001GC000252).

Credit: Peter Bird; Hugo Ahlenius / Nordpil for the GIS conversion; and csterling for the GeoJSON conversion. The upstream collection specifies the **Open Data Commons Attribution License 1.0**. See the [upstream license notice](https://github.com/fraxen/tectonicplates/blob/master/LICENSE.md) and [license text](https://opendatacommons.org/licenses/by/1-0/).

The supplied source GeoJSON is retained. App displays break date-line crossings and draw supplied boundaries without online map tiles; they do not replace or modify the source dataset.

## Project software

No project software license has been selected by the authors. These third-party notices do not license the group's code. The authors should agree on a software license before advertising reuse permissions.
