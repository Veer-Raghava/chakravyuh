# assets/

Vendored, offline. Nothing here is fetched at runtime.

- `models/diya-placeholder.ts` — procedural low-poly teardrop flame. Swap for a real
  Draco `.glb` here later; only the import changes.
- `matcaps/` — **BLOCKED (no network in this env).** Add two CC0 warm clay/ceramic
  matcaps, 256px. See command below.
- `geo/` — **BLOCKED (no network).** Add a low-res coastline GeoJSON. See command below.

## Run these once with network on (both are CC0 / public domain):

```bash
cd apps/drishti-v2/public/assets
# CC0 matcaps (nidorx/matcaps, public domain) — warm clay + warm ceramic:
curl -fL -o matcaps/clay-warm.png    "https://raw.githubusercontent.com/nidorx/matcaps/master/256/C7B299_E9DBC8_8E7A64_9B8974.png"
curl -fL -o matcaps/ceramic-warm.png "https://raw.githubusercontent.com/nidorx/matcaps/master/256/E6BF3C_5A4719_977726_FCFC82.png"
# Natural Earth 110m coastline (public domain):
curl -fL -o geo/coastline-110m.geojson "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_coastline.geojson"
```
