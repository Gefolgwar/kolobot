---
name: h3-js
description: Index points into a hexagonal grid
argument-hint: [function or topic]
---

# H3 Geospatial Indexing — h3-js v4

H3 is Uber's hierarchical hexagonal geospatial indexing system. It tiles the sphere with hexagons at 16 resolutions (0-15), each ~7x finer than the last. The `h3-js` library provides JavaScript bindings for the H3 C library via emscripten.

```
npm install h3-js
```

```js
import * as h3 from "h3-js"; // ESM
const h3 = require("h3-js"); // CJS
```

## When to Use H3

- **Aggregation** — Bucket points into uniform cells with equidistant neighbors for heatmaps and density analysis.
- **Joining disparate datasets** — Index points, lines, and polygons into H3 cells to join datasets that share no common key except location.
- **Flow modeling** — Model movement between cells via directed edges. Uniform neighbor distances simplify weighting.
- **Machine learning** — Apply convolution and other CV techniques to the hex grid using k-rings and IJ coordinates.
- **Multi-resolution analysis** — Compact large cell sets into mixed-resolution representations, then uncompact for comparison at any resolution.

## H3 vs Alternatives

| System               | Cell Shape | Hierarchy                           | Identifiers            | Key Tradeoff                                           |
| -------------------- | ---------- | ----------------------------------- | ---------------------- | ------------------------------------------------------ |
| **H3**               | Hexagon    | Aperture 7, approximate containment | 64-bit int             | Equidistant neighbors; approximate subdivision         |
| **S2**               | Square     | Aperture 4, exact containment       | 64-bit int             | Exact subdivision; non-equidistant neighbors           |
| **Geohash**          | Rectangle  | Exact containment                   | Variable-length string | Simple encoding; severe area distortion at poles       |
| **Hexbin**           | Hexagon    | None                                | Projection-specific    | Cheap to compute; no hierarchy, not portable           |
| **Admin boundaries** | Irregular  | None                                | Names/codes            | Human-meaningful; incomparable sizes, change over time |

## Concepts

Understand these before using the API — they affect correctness.

### Terminology

- **Cell** — A hexagon or pentagon in the H3 grid. Use "cell" in code; "hexagon"/"pentagon" only when the distinction matters.
- **H3Index** — 64-bit integer identifying any H3 object (cell, directed edge, or vertex). Represented as a 15-16 char hex string (e.g., `"85283473fffffff"`).
- **Directed edge** — H3Index (mode 2) representing traversal from one cell to an adjacent cell.
- **Vertex** — H3Index representing a topological vertex of a cell.
- **Base cell** — One of 122 resolution-0 cells (110 hexagons, 12 pentagons). Every cell descends from one.
- **Grid distance** — Minimum number of hops across adjacent cells from one cell to another.

### Pentagons

12 pentagons per resolution, centered on icosahedron vertices (all in ocean — land apps rarely hit them). Most functions handle pentagons transparently. **Exceptions:**

- `gridRing` can throw near pentagons — use `gridDisk` as the safe alternative.
- `gridDistance`, `gridPathCells`, and `cellToLocalIj` may fail across pentagonal distortion.
- Pentagon area is ~50% of hexagon area at the same resolution.

### Hierarchical Containment Is Approximate

Child cell centers may fall outside their parent's boundary. Geographic containment is approximate; logical containment is exact. Use `cellToParent`/`cellToChildren` for logical hierarchy. For exact boundaries, combine H3 indexing with point-in-polygon checks.

`compactCells` / `uncompactCells` use logical containment and are exact.

### Class II vs Class III

Resolutions alternate orientation by ~19.1 degrees. Even (0, 2, 4, ...) = Class II; odd (1, 3, 5, ...) = Class III. Matters for algorithms depending on grid alignment.

### Coordinate Conventions

- Default coordinate order is **lat/lng**. Pass `true` as the `formatAsGeoJson` / `isGeoJson` parameter for **lng/lat** (GeoJSON) order.
- The coordinate reference system uses WGS84/EPSG:4326 with the authalic sphere radius.
- `cellToBoundary` may return more than 6 vertices for cells that cross icosahedron face boundaries.

### Error Handling

Invalid inputs throw errors. Check `.message` for details.

```js
try {
  h3.cellToChildrenSize("invalid", 9);
} catch (e) {
  console.error(e.message); // "Cell argument was not valid"
}
```

Common causes: invalid cell/edge/vertex, incompatible resolutions, cells too far apart for grid distance, pentagon distortion.

## Resolution Guide

Each finer resolution has ~7x more cells. Total cells at resolution r: `2 + 120 * 7^r`.

| Res | Avg Hex Area  | Avg Edge Length | Total Cells   | Typical Use Case |
| --- | ------------- | --------------- | ------------- | ---------------- |
| 0   | 4,357,449 km2 | 1,281 km        | 122           | Continental      |
| 3   | 12,393 km2    | 69 km           | 41,162        | Country / state  |
| 5   | 253 km2       | 9.9 km          | 2,016,842     | Metro area       |
| 7   | 5.16 km2      | 1.4 km          | 98,825,162    | Neighborhood     |
| 9   | 0.105 km2     | 201 m           | 4.8 billion   | City block       |
| 11  | 0.00215 km2   | 28.7 m          | 237 billion   | Building         |
| 13  | 43.9 m2       | 4.1 m           | 11.6 trillion | Room             |
| 15  | 0.9 m2        | 0.58 m          | 569 trillion  | Sub-meter        |

## Common Patterns

### Find all cells within a radius of a point

Convert a radius (km) to a k-ring step count via average edge length.

```js
const origin = h3.latLngToCell(lat, lng, 8);
const radiusKm = 4;
const edgeKm = h3.getHexagonEdgeLengthAvg(8, h3.UNITS.km);
const k = Math.floor(radiusKm / (edgeKm * 2));
const nearby = h3.gridDisk(origin, k);
```

### Aggregate points into hex bins (heatmap)

Count points per cell for density visualization or analysis.

```js
function aggregatePoints(points, res) {
  const counts = {};
  for (const { lat, lng } of points) {
    const cell = h3.latLngToCell(lat, lng, res);
    counts[cell] = (counts[cell] || 0) + 1;
  }
  return counts;
}
```

### Weight points with distance falloff

Spread each point's influence across surrounding cells with linear decay by grid distance.

```js
function weightWithFalloff(points, res, kRadius) {
  const weights = {};
  const step = 1 / (kRadius + 1);
  for (const { lat, lng } of points) {
    const origin = h3.latLngToCell(lat, lng, res);
    const rings = h3.gridDiskDistances(origin, kRadius);
    rings.forEach((ring, dist) => {
      for (const cell of ring) {
        weights[cell] = (weights[cell] || 0) + 1 - dist * step;
      }
    });
  }
  return weights;
}
```

### Compact and uncompact cell sets

Reduce storage for large cell sets. All input cells must share the same resolution.

```js
const cells = h3.polygonToCells(polygon, 9);
const compact = h3.compactCells(cells); // mixed-resolution, fewer cells
const restored = h3.uncompactCells(compact, 9); // back to uniform res 9
```

## GeoJSON Interop

### Coordinate Order

h3-js defaults to **lat/lng** (`[37.77, -122.41]`). GeoJSON requires **lng/lat** (`[-122.41, 37.77]`). Pass `true` for the `isGeoJson`/`formatAsGeoJson` parameter to switch. **Most common integration bug: forgetting this.**

### Convert a single cell to a GeoJSON Feature

`cellToBoundary` returns coordinate arrays, not GeoJSON objects. Wrap manually.

```js
function cellToFeature(cell, properties = {}) {
  const boundary = h3.cellToBoundary(cell, true); // true = GeoJSON [lng, lat] order
  return {
    type: "Feature",
    properties: { h3index: cell, ...properties },
    geometry: {
      type: "Polygon",
      coordinates: [[...boundary, boundary[0]]], // close the ring
    },
  };
}
```

### Convert a set of cells to a GeoJSON FeatureCollection

One polygon feature per cell — useful for choropleth styling.

```js
function cellsToFeatureCollection(cells, getProperties = () => ({})) {
  return {
    type: "FeatureCollection",
    features: cells.map((cell) => cellToFeature(cell, getProperties(cell))),
  };
}
```

### Convert a set of cells to a merged GeoJSON outline

`cellsToMultiPolygon` merges adjacent cells into polygon outlines. All cells must share the same resolution with no duplicates — undefined behavior otherwise.

```js
function cellsToOutlineFeature(cells) {
  const coordinates = h3.cellsToMultiPolygon(cells, true); // true = GeoJSON order
  return {
    type: "Feature",
    properties: {},
    geometry: { type: "MultiPolygon", coordinates },
  };
}
```

### Convert a GeoJSON polygon to H3 cells

Pass `isGeoJson = true` so h3-js reads coordinates in lng/lat order.

```js
function featureToCells(feature, res) {
  const coords = feature.geometry.coordinates;
  // coords[0] = outer ring, coords[1..n] = holes
  return h3.polygonToCells(coords, res, true);
}
```

### Control containment mode when filling polygons

`polygonToCells` uses center containment by default — includes a cell only if its center is inside the polygon. Use `polygonToCellsExperimental` for other modes.

```js
// Include cells that overlap the polygon boundary at all (fuller coverage)
h3.polygonToCellsExperimental(
  coords,
  res,
  h3.POLYGON_TO_CELLS_FLAGS.containment_overlapping,
  true,
);

// Include only cells fully contained within the polygon (stricter)
h3.polygonToCellsExperimental(
  coords,
  res,
  h3.POLYGON_TO_CELLS_FLAGS.containment_full,
  true,
);
```

### geojson2h3 companion library

[`geojson2h3`](https://github.com/uber/geojson2h3) provides higher-level conversion helpers:

```
npm install geojson2h3
```

```js
import geojson2h3 from "geojson2h3";

// GeoJSON Feature → cell set
const cells = geojson2h3.featureToH3Set(geojsonFeature, res);

// Cell set → GeoJSON FeatureCollection (one Feature per cell)
const fc = geojson2h3.h3SetToFeatureCollection(cells, (cell) => ({
  value: data[cell],
}));

// Cell set → single merged GeoJSON Feature (outline)
const outline = geojson2h3.h3SetToFeature(cells);
```

## API Reference

### Indexing

```js
h3.latLngToCell(lat, lng, resolution)    // → "85283473fffffff"
h3.cellToLatLng(cell)                     // → [lat, lng] (center point)
h3.cellToBoundary(cell, formatAsGeoJson?) // → [[lat, lng], ...] (vertices)
```

### Inspection

```js
h3.getResolution(cell); // → number (0-15)
h3.isValidCell(cell); // → boolean
h3.isPentagon(cell); // → boolean
h3.isResClassIII(cell); // → boolean
h3.getBaseCellNumber(cell); // → number (0-121)
h3.getIcosahedronFaces(cell); // → [faceNum, ...]
```

### Hierarchy

```js
h3.cellToParent(cell, parentRes); // → cell
h3.cellToChildren(cell, childRes); // → [cell, ...]
h3.cellToCenterChild(cell, childRes); // → cell
h3.compactCells(cells); // → mixed-resolution compact set
h3.uncompactCells(cells, res); // → uniform-resolution expanded set
h3.cellToChildPos(child, parentRes); // → position index
h3.childPosToCell(childPos, parent, childRes); // → cell
```

### Traversal

```js
h3.gridDisk(origin, k); // filled disk within k steps (safe near pentagons)
h3.gridDiskDistances(origin, k); // disk grouped by distance → [[ring0], [ring1], ...]
h3.gridRing(origin, k); // hollow ring at exactly k steps (may throw near pentagons)
h3.gridDistance(a, b); // grid distance (same resolution; may fail across pentagons)
h3.gridPathCells(start, end); // path of cells (inclusive; may fail across pentagons)
h3.cellToLocalIj(origin, cell); // → {i, j} (experimental; local to origin)
h3.localIjToCell(origin, { i, j }); // → cell (experimental)
```

### Regions

```js
// polygon = array of coordinate rings; first is outer boundary, rest are holes
h3.polygonToCells(polygon, res, isGeoJson?)
h3.cellsToMultiPolygon(cells, formatAsGeoJson?)  // all cells same res, no duplicates
h3.polygonToCellsExperimental(polygon, res, flags, isGeoJson?)
// flags: containment_center (default), containment_full, containment_overlapping, containment_overlapping_bbox
```

### Directed Edges

```js
h3.areNeighborCells(a, b); // → boolean
h3.cellsToDirectedEdge(origin, dest); // → edge index
h3.getDirectedEdgeOrigin(edge); // → cell
h3.getDirectedEdgeDestination(edge); // → cell
h3.directedEdgeToCells(edge); // → [origin, dest]
h3.originToDirectedEdges(cell); // → [edge, ...] (all 6 or 5 edges)
h3.directedEdgeToBoundary(edge); // → [[lat, lng], ...]
```

### Vertexes

```js
h3.cellToVertex(cell, vertexNum); // → vertex index (0-5 hex, 0-4 pentagon)
h3.cellToVertexes(cell); // → [vertex, ...]
h3.vertexToLatLng(vertex); // → [lat, lng]
h3.isValidVertex(vertex); // → boolean
```

### Metrics & Utilities

```js
h3.getHexagonAreaAvg(res, h3.UNITS.km2); // average hex area at resolution
h3.getHexagonEdgeLengthAvg(res, h3.UNITS.km); // average edge length at resolution
h3.cellArea(cell, h3.UNITS.km2); // exact area of a specific cell
h3.edgeLength(edge, h3.UNITS.km); // exact length of a specific edge
h3.getNumCells(res); // total cell count at resolution
h3.greatCircleDistance(point1, point2, h3.UNITS.km); // haversine distance ([lat,lng] points)
h3.getRes0Cells(); // all 122 base cells
h3.getPentagons(res); // 12 pentagons at resolution
h3.degsToRads(degrees);
h3.radsToDegs(radians);
```

Units: `h3.UNITS.km2`, `h3.UNITS.m2`, `h3.UNITS.rads2`, `h3.UNITS.km`, `h3.UNITS.m`, `h3.UNITS.rads`

## v3 to v4 Migration

Function names changed in v4. The grid itself is unchanged — indexes from v3 are valid in v4.

| v3                      | v4                    |
| ----------------------- | --------------------- |
| `geoToH3`               | `latLngToCell`        |
| `h3ToGeo`               | `cellToLatLng`        |
| `h3ToGeoBoundary`       | `cellToBoundary`      |
| `kRing`                 | `gridDisk`            |
| `hexRing`               | `gridRing`            |
| `h3Distance`            | `gridDistance`        |
| `h3ToParent`            | `cellToParent`        |
| `h3ToChildren`          | `cellToChildren`      |
| `polyfill`              | `polygonToCells`      |
| `h3SetToMultiPolygon`   | `cellsToMultiPolygon` |
| `compact`               | `compactCells`        |
| `uncompact`             | `uncompactCells`      |
| `h3IndexesAreNeighbors` | `areNeighborCells`    |

See [reference.md](reference.md) for the complete function name mapping.

## Full Documentation

Complete API reference, algorithm internals, community libraries, and 40+ Observable notebooks in [reference.md](reference.md).
