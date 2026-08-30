# === api/directededge ===

---

id: uniedge
title: Directed edge functions
sidebar_label: Directed edges
slug: /api/uniedge

---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

Directed edges allow encoding the directed (that is, which cell is the origin and which is the destination can be determined)
edge from one cell to a neighboring cell.

## areNeighborCells

Determines whether or not the provided H3 cells are neighbors.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error areNeighborCells(H3Index origin, H3Index destination, int *out);
```

`out` will be 1 if the indexes are neighbors, 0 otherwise.

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
boolean areNeighborCells(long origin, long destination);
boolean areNeighborCells(String origin, String destination);
```

</TabItem>
<TabItem value="javascript">

```js
h3.areNeighborCells(origin, destination);
```

```js live
function example() {
  const origin = "85283473fffffff";
  const destination = "85283477fffffff";
  return h3.areNeighborCells(origin, destination);
}
```

</TabItem>
<TabItem value="python">

```py
h3.are_neighbor_cells(origin, destination)
```

</TabItem>
<TabItem value="go">

```go
origin.IsNeighbor(destination)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_are_neighbor_cells(origin, destination)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 areNeighborCells --help
h3: Determines if the provided H3 cells are neighbors (have a shared border)
H3 4.1.0

	areNeighborCells	Determines if the provided H3 cells are neighbors (have a shared border)
	-o, --origin <CELL>	Required. Origin H3 Cell
	-d, --destination <CELL>	Required. Destination H3 Cell
	-h, --help	Show this help message.
	-f, --format <FMT>	'json' for true or false, 'numeric' for 1 or 0 (Default: json)
```

```bash
$ h3 areNeighborCells -o 85283473fffffff -d 85283477fffffff
true
```

</TabItem>
</Tabs>

## cellsToDirectedEdge

Provides a directed edge H3 index based on the provided origin and
destination.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error cellsToDirectedEdge(H3Index origin, H3Index destination, H3Index *out);
```

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
long cellsToDirectedEdge(long origin, long destination);
String cellsToDirectedEdge(String origin, String destination);
```

</TabItem>
<TabItem value="javascript">

```js
h3.cellsToDirectedEdge(h3Index);
```

```js live
function example() {
  const origin = "85283473fffffff";
  const destination = "85283477fffffff";
  return h3.cellsToDirectedEdge(origin, destination);
}
```

</TabItem>
<TabItem value="python">

```py
h3.cells_to_directed_edge(origin, destination)
```

</TabItem>
<TabItem value="go">

```go
origin.DirectedEdge(destination)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_cells_to_directed_edge(origin, destination)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 cellsToDirectedEdge --help
h3: Converts neighboring cells into a directed edge index (or errors if they are not neighbors)
H3 4.1.0

	cellsToDirectedEdge	Converts neighboring cells into a directed edge index (or errors if they are not neighbors)
	-o, --origin <CELL>	Required. Origin H3 Cell
	-d, --destination <CELL>	Required. Destination H3 Cell
	-h, --help	Show this help message.
	-f, --format <FMT>	'json' for "CELL"\n, 'newline' for CELL\n (Default: json)
```

```bash
$ h3 cellsToDirectedEdge -o 85283473fffffff -d 85283477fffffff
"115283473fffffff"
```

</TabItem>
</Tabs>

## isValidDirectedEdge

Determines if the provided H3Index is a valid unidirectional edge index.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
int isValidDirectedEdge(H3Index edge);
```

Returns `1` if it is a unidirectional edge H3Index, otherwise `0`.

</TabItem>
<TabItem value="java">

```java
boolean isValidDirectedEdge(long edge);
boolean isValidDirectedEdge(String edgeAddress);
```

</TabItem>
<TabItem value="javascript">

```js
h3.isValidDirectedEdge(edge);
```

```js live
function example() {
  const edge = "115283473fffffff";
  return h3.isValidDirectedEdge(edge);
}
```

</TabItem>
<TabItem value="python">

```py
h3.is_valid_directed_edge(edge)
```

</TabItem>
<TabItem value="go">

```go
edge.IsValid()
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_is_valid_directed_edge(edge)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 isValidDirectedEdge --help
h3: Checks if the provided H3 directed edge is actually valid
H3 4.1.0

	isValidDirectedEdge	Checks if the provided H3 directed edge is actually valid
	-h, --help	Show this help message.
	-c, --cell <index>	Required. H3 Cell
	-f, --format <FMT>	'json' for true or false, 'numeric' for 1 or 0 (Default: json)
```

```bash
$ h3 isValidDirectedEdge -c 115283473fffffff
true
```

</TabItem>
</Tabs>

## getDirectedEdgeOrigin

Provides the origin hexagon from the directed edge H3Index.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error getDirectedEdgeOrigin(H3Index edge, H3Index *out);
```

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
long getDirectedEdgeOrigin(long edge);
String getDirectedEdgeOrigin(String edgeAddress);
```

</TabItem>
<TabItem value="javascript">

```js
h3.getDirectedEdgeOrigin(h3Index);
```

```js live
function example() {
  const edge = "115283473fffffff";
  return h3.getDirectedEdgeOrigin(edge);
}
```

</TabItem>
<TabItem value="python">

```py
h3.get_directed_edge_origin(edge)
```

</TabItem>
<TabItem value="go">

```go
edge.Origin()
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_get_directed_edge_origin(edge)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 getDirectedEdgeOrigin --help
h3: Returns the origin cell from the directed edge
H3 4.1.0

	getDirectedEdgeOrigin	Returns the origin cell from the directed edge
	-c, --cell <index>	Required. H3 Cell
	-h, --help	Show this help message.
	-f, --format <FMT>	'json' for "CELL"\n, 'newline' for CELL\n (Default: json)
```

```bash
$ h3 getDirectedEdgeOrigin -c 115283473fffffff
"85283473fffffff"
```

</TabItem>
</Tabs>

## getDirectedEdgeDestination

Provides the destination hexagon from the directed edge H3Index.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error getDirectedEdgeDestination(H3Index edge, H3Index *out);
```

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
long getDirectedEdgeDestination(long edge);
String getDirectedEdgeDestination(String edgeAddress);
```

</TabItem>
<TabItem value="javascript">

```js
h3.getDirectedEdgeDestination(edge);
```

```js live
function example() {
  const edge = "115283473fffffff";
  return h3.getDirectedEdgeDestination(edge);
}
```

</TabItem>
<TabItem value="python">

```py
h3.get_directed_edge_destination(edge)
```

</TabItem>
<TabItem value="go">

```go
edge.Destination()
```

</TabItem>
<TabItem value="duckdb">

```sql
h3.get_directed_edge_destination(edge)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 getDirectedEdgeDestination --help
h3: Returns the destination cell from the directed edge
H3 4.1.0

	getDirectedEdgeDestination	Returns the destination cell from the directed edge
	-c, --cell <index>	Required. H3 Cell
	-h, --help	Show this help message.
	-f, --format <FMT>	'json' for "CELL"\n, 'newline' for CELL\n (Default: json)
```

```bash
$ h3 getDirectedEdgeDestination -c 115283473fffffff
"85283477fffffff"
```

</TabItem>
</Tabs>

## directedEdgeToCells

Provides the origin-destination pair of cells for the given directed edge.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error directedEdgeToCells(H3Index edge, H3Index* originDestination);
```

The origin and destination are placed at
`originDestination[0]` and `originDestination[1]`, respectively.

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
List<Long> directedEdgeToCells(long edge);
List<String> directedEdgeToCells(String edgeAddress);
```

</TabItem>
<TabItem value="javascript">

```js
h3.directedEdgeToCells(edge);
```

```js live
function example() {
  const edge = "115283473fffffff";
  return h3.directedEdgeToCells(edge);
}
```

</TabItem>
<TabItem value="python">

```py
h3.directed_edge_to_cells(edge)
```

</TabItem>
<TabItem value="go">

```go
edge.Cells()
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_directed_edge_to_cells(edge)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 directedEdgeToCells --help
h3: Returns the origin, destination pair of cells from the directed edge
H3 4.1.0

	directedEdgeToCells	Returns the origin, destination pair of cells from the directed edge
	-c, --cell <index>	Required. H3 Cell
	-h, --help	Show this help message.
	-f, --format <FMT>	'json' for ["CELL", ...], 'newline' for CELL\n... (Default: json)
```

```bash
$ h3 directedEdgeToCells -c 115283473fffffff
["85283473fffffff", "85283477fffffff"]
```

</TabItem>
</Tabs>

## originToDirectedEdges

Provides all of the directed edges from the current cell.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error originToDirectedEdges(H3Index origin, H3Index* edges);
```

`edges` must be of length 6,
and the number of directed edges placed in the array may be less than 6.
If this is the case, one of the members of the array will be `0`.

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
List<Long> originToDirectedEdges(long h3);
List<String> originToDirectedEdges(String h3);
```

</TabItem>
<TabItem value="javascript">

```js
h3.originToDirectedEdges(h3Index);
```

```js live
function example() {
  const h = "85283473fffffff";
  return h3.originToDirectedEdges(h);
}
```

</TabItem>
<TabItem value="python">

```py
h3.origin_to_directed_edges(h)
```

</TabItem>
<TabItem value="go">

```go
origin.DirectedEdges()
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_origin_to_directed_edges(h)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 originToDirectedEdges --help
h3: Returns all of the directed edges from the specified origin cell
H3 4.1.0

	originToDirectedEdges	Returns all of the directed edges from the specified origin cell
	-c, --cell <index>	Required. H3 Cell
	-h, --help	Show this help message.
	-f, --format <FMT>	'json' for ["CELL", ...], 'newline' for CELL\n... (Default: json)
```

```bash
$ h3 originToDirectedEdges -c 85283473fffffff
["115283473fffffff", "125283473fffffff", "135283473fffffff", "145283473fffffff", "155283473fffffff", "165283473fffffff"]
```

</TabItem>
</Tabs>

## directedEdgeToBoundary

Provides the geographic lat/lng coordinates defining the directed edge.
Note that this may be more than two points for complex edges.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error directedEdgeToBoundary(H3Index edge, CellBoundary* gb);
```

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
List<LatLng> directedEdgeToBoundary(long edge);
List<LatLng> directedEdgeToBoundary(String edgeAddress);
```

</TabItem>
<TabItem value="javascript">

```js
h3.directedEdgeToBoundary(edge, [formatAsGeoJson]);
```

```js live
function example() {
  const edge = "115283473fffffff";
  return h3.directedEdgeToBoundary(edge);
}
```

</TabItem>
<TabItem value="python">

```py
h3.directed_edge_to_boundary(edge)
```

</TabItem>
<TabItem value="go">

```go
edge.Boundary()
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_directed_edge_to_boundary(edge)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 directedEdgeToBoundary --help
h3: Provides the coordinates defining the directed edge
H3 4.1.0

	directedEdgeToBoundary	Provides the coordinates defining the directed edge
	-c, --cell <index>	Required. H3 Cell
	-h, --help	Show this help message.
	-f, --format <FMT>	'json' for [[lat, lng], ...], 'wkt' for a WKT POLYGON, 'newline' for lat\nlng\n... (Default: json)
```

```bash
$ h3 directedEdgeToBoundary -c 115283473fffffff
[[37.4201286777, -122.0377349643], [37.3375560844, -122.0904289290]]
```

</TabItem>
</Tabs>

## reverseDirectedEdge

Returns the directed edge index that represents the same edge in the opposite direction (i.e., with origin and destination cells swapped).

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]}

> <TabItem value="c">

```c
H3Error reverseDirectedEdge(H3Index edge, H3Index* out);
```

Takes a directed edge H3Index and returns (via out) the directed edge H3Index representing the edge in the reverse direction. Returns an error if the input is not a valid directed edge.

</TabItem>
<TabItem value="java">

```java
long reverseDirectedEdge(long edge);
String reverseDirectedEdge(String edgeAddress);
```

</TabItem>
<TabItem value="javascript">

```js
h3.reverseDirectedEdge(edge);
```

```js live
function example() {
  const edge = "115283473fffffff";
  return h3.reverseDirectedEdge(edge);
}
```

</TabItem>
<TabItem value="python">

```py
h3.reverse_directed_edge(edge)
```

</TabItem>
<TabItem value="go">

```go
edge.Reverse()
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_reverse_directed_edge(edge)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 reverseDirectedEdge --help
h3: Returns the directed edge index representing the same edge in the opposite direction
H3 4.1.0

  reverseDirectedEdge Returns the directed edge index representing the same edge in the opposite direction
  -e, --edge <EDGE> Required. Directed edge H3 index
  -h, --help  Show this help message.
  -f, --format <FMT>  'json' for "EDGE"\n, 'newline' for EDGE\n (Default: json)
```

```bash
$ h3 reverseDirectedEdge -e 115283473fffffff
"115283477fffffff"
```

</TabItem>
</Tabs>

# === api/hierarchy ===

---

id: hierarchy
title: Hierarchical grid functions
sidebar_label: Hierarchy
slug: /api/hierarchy

---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

These functions permit moving between resolutions in the H3 grid system.
The functions produce parent cells (coarser), or child cells (finer).

## cellToParent

Provides the unique ancestor (coarser) cell of the given `cell` for
the provided resolution. If the input cell has resolution `r`, then
`parentRes = r - 1` would give the immediate parent,
`parentRes = r - 2` would give the grandparent, and so on.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error cellToParent(H3Index cell, int parentRes, H3Index *parent);
```

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
long cellToParent(long cell, int parentRes);
String cellToParentAddress(String cellAddress, int parentRes);
```

</TabItem>
<TabItem value="javascript">

```js
h3.cellToParent(cell, parentRes);
```

```js live
function example() {
  const cell = "85283473fffffff";
  return h3.cellToParent(cell, 4);
}
```

</TabItem>
<TabItem value="python">

```py
h3.cell_to_parent(h, res=None)
```

If `res = None`, we set `res = resolution(h) - 1`.
See the [h3-py docs](https://uber.github.io/h3-py/api_verbose.html#h3.cell_to_parent).

</TabItem>
<TabItem value="go">

```go
cell.Parent(res)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_cell_to_parent(h, res)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 cellToParent --help
h3: Returns the H3 index that is the parent (or higher) of the provided cell
H3 4.1.0

	cellToParent	Returns the H3 index that is the parent (or higher) of the provided cell
	-h, --help	Show this help message.
	-c, --cell <index>	Required. H3 Cell
	-r, --resolution <res>	Required. Resolution, 0-14 inclusive, excluding 15 as it can never be a parent
	-f, --format <FMT>	'json' for "CELL"\n, 'newline' for CELL\n (Default: json)
```

```bash
$ h3 cellToParent -c 85283473fffffff -r 4
"8428347ffffffff"
```

</TabItem>
</Tabs>

## cellToChildren

Provides the children (descendant) cells of `cell` at
resolution `childRes`.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error cellToChildren(H3Index cell, int childRes, H3Index *children);
```

`children` must be an array of at least size `cellToChildrenSize(cell, childRes)`.

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
List<Long> cellToChildren(long cell, int childRes);
List<String> cellToChildren(String cellAddress, int childRes);
```

</TabItem>
<TabItem value="javascript">

```js
h3.cellToChildren(cell, childRes);
```

```js live
function example() {
  const cell = "85283473fffffff";
  return h3.cellToChildren(cell, 6);
}
```

</TabItem>
<TabItem value="python">

```py
h3.cell_to_children(h, res=None)
```

If `res = None`, we set `res = resolution(h) + 1`.
See the [h3-py docs](https://uber.github.io/h3-py/api_verbose.html#h3.cell_to_children).

</TabItem>
<TabItem value="go">

```go
cell.Children(res)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_cell_to_children(h, res)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 cellToChildren --help
h3: Returns an array of H3 indexes that are the children (or lower) of the provided cell
H3 4.1.0

	cellToChildren	Returns an array of H3 indexes that are the children (or lower) of the provided cell
	-h, --help	Show this help message.
	-c, --cell <index>	Required. H3 Cell
	-r, --resolution <res>	Required. Resolution, 1-15 inclusive, excluding 0 as it can never be a child
	-f, --format <FMT>	'json' for ["CELL", ...], 'newline' for CELL\n... (Default: json)
```

```bash
$ h3 cellToChildren -c 85283473fffffff -r 6
[ "862834707ffffff", "86283470fffffff", "862834717ffffff", "86283471fffffff", "862834727ffffff", "86283472fffffff", "862834737ffffff" ]
```

</TabItem>
</Tabs>

## cellToChildrenSize

Provides the number of children at a given resolution of the given cell.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error cellToChildrenSize(H3Index cell, int childRes, int64_t *out);
```

Provides the size of the `children` array needed for the given inputs to `cellToChildren`.

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
long cellToChildrenSize(long cell, int childRes);
long cellToChildrenSize(String cellAddress, int childRes);
```

</TabItem>
<TabItem value="javascript">

```js
h3.cellToChildrenSize(cell, childRes);
```

```js live
function example() {
  const cell = "85283473fffffff";
  return h3.cellToChildrenSize(cell, 6);
}
```

</TabItem>
<TabItem value="python">

```py
h3.cell_to_children_size(h, res=None)
```

If `res = None`, we set `res = resolution(h) + 1`.
See the [h3-py docs](https://uber.github.io/h3-py/api_verbose.html#h3.cell_to_children_size).

</TabItem>
<TabItem value="go">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="duckdb">

```sql
h3_cell_to_children_size(h, res)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 cellToChildrenSize --help
h3: Returns the maximum number of children for a given cell at the specified child resolution
H3 4.1.0

	cellToChildrenSize	Returns the maximum number of children for a given cell at the specified child resolution
	-h, --help	Show this help message.
	-c, --cell <index>	Required. H3 Cell
	-r, --resolution <res>	Required. Resolution, 1-15 inclusive, excluding 0 as it can never be a child
```

```bash
$ h3 cellToChildrenSize -c 85283473fffffff -r 6
7
```

</TabItem>
</Tabs>

## cellToCenterChild

Provides the center child (finer) cell contained by `cell` at resolution `childRes`.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error cellToCenterChild(H3Index cell, int childRes, H3Index *child);
```

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
long cellToCenterChild(long cell, int childRes);
String cellToCenterChild(String cellAddress, int childRes);
```

</TabItem>
<TabItem value="javascript">

```js
h3.cellToCenterChild(cell, childRes);
```

```js live
function example() {
  const cell = "85283473fffffff";
  return h3.cellToCenterChild(cell, 7);
}
```

</TabItem>
<TabItem value="python">

```py
h3.cell_to_center_child(h, res=None)
```

If `res = None`, we set `res = resolution(h) + 1`.
See the [h3-py docs](https://uber.github.io/h3-py/api_verbose.html#h3.cell_to_center_child).

</TabItem>
<TabItem value="go">

```go
cell.CenterChild(res)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_cell_to_center_child(h, res)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 cellToCenterChild --help
h3: Returns the H3 index that is the centrally-placed child (or lower) of the provided cell
H3 4.1.0

	cellToCenterChild	Returns the H3 index that is the centrally-placed child (or lower) of the provided cell
	-h, --help	Show this help message.
	-c, --cell <index>	Required. H3 Cell
	-r, --resolution <res>	Required. Resolution, 1-15 inclusive, excluding 0 as it can never be a child
	-f, --format <FMT>	'json' for "CELL"\n, 'newline' for CELL\n (Default: json)
```

```bash
$ h3 cellToCenterChild -c 85283473fffffff -r 7
"872834700ffffff"
```

</TabItem>
</Tabs>

## cellToChildPos

Provides the position of the child cell within an ordered list of all children of the cell's parent at the specified resolution `parentRes`.
The order of the ordered list is the same as that returned by `cellToChildren`.
This is the complement of `childPosToCell`.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error cellToChildPos(H3Index child, int parentRes, int64_t *out);
```

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
long cellToChildPos(long child, int parentRes);
long cellToChildPos(String childAddress, int parentRes);
```

</TabItem>
<TabItem value="javascript">

```js
h3.cellToChildPos(child, parentRes);
```

```js live
function example() {
  const cell = "85283473fffffff";
  return h3.cellToChildPos(cell, 3);
}
```

</TabItem>
<TabItem value="python">

```py
h3.cell_to_child_pos(child, res_parent)
```

</TabItem>
<TabItem value="go">

```go
child.ChildPos(parentRes)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_cell_to_child_pos(child, res_parent)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 cellToChildPos --help
h3: Returns the position of the child cell within an ordered list of all children of the cell's parent at the specified child resolution
H3 4.1.0

	cellToChildPos	Returns the position of the child cell within an ordered list of all children of the cell's parent at the specified child resolution
	-h, --help	Show this help message.
	-c, --cell <index>	Required. H3 Cell
	-r, --resolution <res>	Required. Resolution, 1-15 inclusive, excluding 0 as it can never be a child
```

```bash
$ h3 cellToChildPos -c 85283473fffffff -r 3
25
```

</TabItem>
</Tabs>

## childPosToCell

Provides the child cell at a given position within an ordered list of all children of `parent` at the specified resolution `childRes`.
The order of the ordered list is the same as that returned by `cellToChildren`.
This is the complement of `cellToChildPos`.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error childPosToCell(int64_t childPos, H3Index parent, int childRes, H3Index *child);
```

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
long childPosToCell(long childPos, long parent, int childRes);
String childPosToCell(long childPos, String parentAddress, int childRes);
```

</TabItem>
<TabItem value="javascript">

```js
h3.childPosToCell(childPos, parent, childRes);
```

```js live
function example() {
  const parent = "85283473fffffff";
  const childPos = 42;
  return h3.childPosToCell(childPos, parent, 7);
}
```

</TabItem>
<TabItem value="python">

```py
h3.child_pos_to_cell(parent, res_child, child_pos)
```

</TabItem>
<TabItem value="go">

```go
parent.ChildPosToCell(childPos, res)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_child_pos_to_cell(child_pos, parent, res_child)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 childPosToCell --help
h3: Returns the child cell at a given position and resolution within an ordered list of all children of the parent cell
H3 4.1.0

	childPosToCell	Returns the child cell at a given position and resolution within an ordered list of all children of the parent cell
	-h, --help	Show this help message.
	-c, --cell <index>	Required. H3 Cell
	-r, --resolution <res>	Required. Resolution, 1-15 inclusive, excluding 0 as it can never be a child
	-p, --position <pos>	Required. The child position within the set of children of the parent cell
	-f, --format <FMT>	'json' for "CELL"\n, 'newline' for CELL\n (Default: json)
```

```bash
$ h3 childPosToCell -p 42 -c 85283473fffffff -r 7
"872834730ffffff"
```

</TabItem>
</Tabs>

## compactCells

Compacts a collection of H3 cells by recursively replacing children cells
with their parents if all children are present.
Input cells must all share the same resolution.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error compactCells(const H3Index *cellSet, H3Index *compactedSet, const int64_t numCells);
```

Compacts `cellSet` into the array `compactedSet`.
`compactedSet` must be at least the size of `cellSet` (in case the set cannot be compacted).

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
List<Long> compactCells(Collection<Long> cells);
List<String> compactCellAddress(Collection<String> cells);
```

</TabItem>
<TabItem value="javascript">

```js
h3.compactCells(cells);
```

```js live
function example() {
  const cell = "85283473fffffff";
  const nearby = h3.gridDisk(cell, 4);
  return h3.compactCells(nearby);
}
```

</TabItem>
<TabItem value="python">

```py
h3.compact_cells(cells)
```

</TabItem>
<TabItem value="go">

```go
h3.CompactCells(cells)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_compact_cells(cells)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 compactCells --help
h3: Compacts the provided set of cells as best as possible. The set of input cells must all share the same resolution.
H3 4.1.0

	compactCells	Compacts the provided set of cells as best as possible. The set of input cells must all share the same resolution.
	-h, --help	Show this help message.
	-i, --file <FILENAME>	The file to load the cells from. Use -- to read from stdin.
	-c, --cells <CELLS>	The cells to compact. Up to 100 cells if provided as hexadecimals with zero padding.
	-f, --format <FMT>	'json' for ["CELL", ...], 'newline' for CELL\n... (Default: json)
```

```bash
$ h3 compactCells -c 85283473fffffff,85283447fffffff,8528347bfffffff,85283463fffffff,85283477fffffff,8528340ffffffff,8528340bfffffff,85283457fffffff,85283443fffffff,8528344ffffffff,852836b7fffffff,8528346bfffffff,8528346ffffffff,85283467fffffff,8528342bfffffff,8528343bfffffff,85283407fffffff,85283403fffffff,8528341bfffffff
[ "85283447fffffff", "8528340ffffffff", "8528340bfffffff", "85283457fffffff", "85283443fffffff", "8528344ffffffff", "852836b7fffffff", "8528342bfffffff", "8528343bfffffff", "85283407fffffff", "85283403fffffff", "8528341bfffffff", "8428347ffffffff" ]
```

</TabItem>
</Tabs>

## uncompactCells

Uncompacts the set `compactedSet` of indexes to the resolution `res`.
`h3Set` must be at least of size `uncompactCellsSize(compactedSet, numHexes, res)`.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error uncompactCells(const H3Index *compactedSet, const int64_t numCells, H3Index *cellSet, const int64_t maxCells, const int res);
```

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
List<Long> uncompactCells(Collection<Long> cells, int res);
List<String> uncompactCellAddress(Collection<String> cells, int res);
```

</TabItem>
<TabItem value="javascript">

```js
h3.uncompactCells(cells, res);
```

```js live
function example() {
  const cell = "85283473fffffff";
  const nearby = h3.gridDisk(cell, 4);
  const compacted = h3.compactCells(nearby);
  return h3.uncompactCells(compacted, 5);
}
```

</TabItem>
<TabItem value="python">

```py
h3.uncompact_cells(cells, res)
```

</TabItem>
<TabItem value="go">

```go
h3.UncompactCells(cells, res)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_uncompact_cells(cells, res)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 uncompactCells --help
h3: Unompacts the provided set of compacted cells.The uncompacted cells will be printed one per line to stdout.
H3 4.1.0

	uncompactCells	Unompacts the provided set of compacted cells.The uncompacted cells will be printed one per line to stdout.
	-h, --help	Show this help message.
	-i, --file <FILENAME>	The file to load the cells from. Use -- to read from stdin.
	-c, --cells <CELLS>	The cells to uncompact. Up to 100 cells if provided as hexadecimals with zero padding.
	-r, --resolution <res>	Required. Resolution, 0-15 inclusive, that the compacted set should be uncompacted to. Must be greater than or equal to the highest resolution within the compacted set.
	-f, --format <FMT>	'json' for ["CELL", ...], 'newline' for CELL\n... (Default: json)
```

```bash
$ h3 uncompactCells -r 5 -c 85283447fffffff,8528340ffffffff,8528340bfffffff,85283457fffffff,85283443fffffff,8528344ffffffff,852836b7fffffff,8528342bfffffff,8528343bfffffff,85283407fffffff,85283403fffffff,8528341bfffffff,8428347ffffffff
[ "85283447fffffff", "8528340ffffffff", "8528340bfffffff", "85283457fffffff", "85283443fffffff", "8528344ffffffff", "852836b7fffffff", "8528342bfffffff", "8528343bfffffff", "85283407fffffff", "85283403fffffff", "8528341bfffffff", "85283463fffffff", "85283467fffffff", "8528346bfffffff", "8528346ffffffff", "85283473fffffff", "85283477fffffff", "8528347bfffffff" ]
```

</TabItem>
</Tabs>

## uncompactCellsSize

Provides the total resulting number of cells if uncompacting a cell set to
a given resolution.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error uncompactCellsSize(const H3Index *compactedSet, const int64_t numCompacted, const int res, int64_t *out);
```

Provides the size of the array needed by `uncompactCells` into `out`.

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="javascript">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="python">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="go">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="duckdb">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="shell">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
</Tabs>

# === api/indexing ===

---

id: indexing
title: Indexing functions
sidebar_label: Indexing
slug: /api/indexing

---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

These functions are used for finding the H3 cell index containing coordinates,
and for finding the center and boundary of H3 cells.

## latLngToCell

Indexes the location at the specified resolution,
providing the index of the cell containing the location.
This buckets the geographic point into the H3 grid.
For more information, see the
[algorithm description](../core-library/latLngToCellDesc).

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error latLngToCell(const LatLng *g, int res, H3Index *out);
```

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
long latLngToCell(double lat, double lng, int res);
String latLngToCellAddress(double lat, double lng, int res);
```

</TabItem>
<TabItem value="javascript">

```js
h3.latLngToCell(lat, lng, res);
```

```js live
function example() {
  const lat = 45;
  const lng = 40;
  const res = 2;
  return h3.latLngToCell(lat, lng, res);
}
```

</TabItem>
<TabItem value="python">

```py
h3.latlng_to_cell(lat, lng, resolution)
```

</TabItem>
<TabItem value="go">

```go
h3.LatLngToCell(h3.NewLatLng(lat, lng), resolution)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_latlng_to_cell(lat, lng, resolution)
```

```sql
h3_latlng_to_cell_string(lat, lng, resolution)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 latLngToCell --help
h3: Convert degrees latitude/longitude coordinate to an H3 cell
H3 4.1.0

	latLngToCell	Convert degrees latitude/longitude coordinate to an H3 cell
	-h, --help	Show this help message.
	-r, --resolution <res>	Required. Resolution, 0-15 inclusive.
	--lat, --latitude <lat>	Required. Latitude in degrees.
	--lng, --longitude <lng>	Required. Longitude in degrees.
	-f, --format <FMT>	'json' for "CELL"\n, 'newline' for CELL\n (Default: json)
```

```bash
$ h3 latLngToCell --lat 45 --lng 40 -r 2
"822d57fffffffff"
```

</TabItem>
</Tabs>

## cellToLatLng

Finds the center of the cell in grid space. See the
[algorithm description](../core-library/cellToLatLngDesc) for
more information.

The center will drift versus the centroid
of the cell on Earth due to distortion from the gnomonic
projection within the icosahedron face it resides on and its
distance from the center of the icosahedron face.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error cellToLatLng(H3Index cell, LatLng *g);
```

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
LatLng cellToLatLng(long cell);
LatLng cellToLatLng(String cellAddress);
```

</TabItem>
<TabItem value="javascript">

```js
h3.cellToLatLng(cell);
```

```js live
function example() {
  const cell = "85283473fffffff";
  return h3.cellToLatLng(cell);
}
```

</TabItem>
<TabItem value="python">

```py
h3.cell_to_latlng(cell)
```

</TabItem>
<TabItem value="go">

```go
h3.CellToLatLng(cell)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_cell_to_latlng(cell)
```

```sql
h3_cell_to_lat(cell)
```

```sql
h3_cell_to_lng(cell)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 cellToLatLng --help
h3: Convert an H3Cell to a coordinate
H3 4.1.0

	cellToLatLng	Convert an H3Cell to a coordinate
	-h, --help	Show this help message.
	-c, --cell <index>	Required. H3 Cell
	-f, --format <FMT>	'json' for [lat, lng], 'wkt' for a WKT POINT, 'newline' for lat\nlng\n (Default: json)
```

```bash
$ h3 cellToLatLng -c 85283473fffffff
[37.3457933754, -121.9763759726]
```

</TabItem>
</Tabs>

## cellToBoundary

Finds the boundary of the cell.
For more information, see the
[algorithm description](../core-library/cellToBoundaryDesc).

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error cellToBoundary(H3Index cell, CellBoundary *bndry);
```

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
List<LatLng> cellToBoundary(long cell);
List<LatLng> cellToBoundary(String cellAddress);
```

</TabItem>
<TabItem value="javascript">

```js
h3.cellToBoundary(cell, [formatAsGeoJson]);
```

```js live
function example() {
  const cell = "85283473fffffff";
  return h3.cellToBoundary(cell);
}
```

</TabItem>
<TabItem value="python">

```py
h3.cell_to_boundary(cell)
```

Returns tuple of lat/lng tuples.
For GeoJSON compatibility (lng/lat order), see the
[`h3-py` docs](https://uber.github.io/h3-py/api_quick.html#polygon-interface).

</TabItem>
<TabItem value="go">

```go
cell.Boundary()
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_cell_to_boundary_wkt(cell)
```

```sql
h3_cell_to_boundary_wkb(cell)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 cellToBoundary --help
h3: Convert an H3 cell to a polygon defining its boundary
H3 4.1.0

	cellToBoundary	Convert an H3 cell to a polygon defining its boundary
	-h, --help	Show this help message.
	-c, --cell <index>	Required. H3 Cell
	-f, --format <FMT>	'json' for [[lat, lng], ...], 'wkt' for a WKT POLYGON, 'newline' for lat\nlng\n... (Default: json)
```

```bash
$ h3 cellToBoundary -c 85283473fffffff
[[37.2713558667, -121.9150803271], [37.3539264509, -121.8622232890], [37.4283411861, -121.9235499963], [37.4201286777, -122.0377349643], [37.3375560844, -122.0904289290], [37.2631979746, -122.0291013092]]
```

</TabItem>
</Tabs>

# === api/inspection ===

---

id: inspection
title: Index inspection functions
sidebar_label: Inspection
slug: /api/inspection

---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

These functions provide metadata about an H3 index, such as its resolution or base cell, and provide utilities for converting into and out of the 64-bit representation of an H3 index.

## getResolution

Returns the resolution of the index.
(Works for cells, edges, and vertexes.)

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
int getResolution(H3Index h);
```

</TabItem>
<TabItem value="java">

```java
int getResolution(long h3);
int getResolution(String h3Address);
```

</TabItem>
<TabItem value="javascript">

```js
h3.getResolution(h);
```

```js live
function example() {
  const h = "85283473fffffff";
  return h3.getResolution(h);
}
```

</TabItem>
<TabItem value="python">

```py
h3.get_resolution(h)
```

</TabItem>
<TabItem value="go">

```go
cell.Resolution()
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_get_resolution(h)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 getResolution --help
h3: Extracts the resolution (0 - 15) from the H3 cell
H3 4.1.0

	getResolution	Extracts the resolution (0 - 15) from the H3 cell
	-h, --help	Show this help message.
	-c, --cell <index>	Required. H3 Cell
```

```bash
$ h3 getResolution -c 85283473fffffff
5
```

</TabItem>
</Tabs>

## getBaseCellNumber

Returns the base cell number of the index.
(Works for cells, edges, and vertexes.)

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
int getBaseCellNumber(H3Index h);
```

</TabItem>
<TabItem value="java">

```java
int getBaseCellNumber(long h3);
int getBaseCellNumber(String h3Address);
```

</TabItem>
<TabItem value="javascript">

```js
h3.getBaseCellNumber(h);
```

```js live
function example() {
  const h = "85283473fffffff";
  return h3.getBaseCellNumber(h);
}
```

</TabItem>
<TabItem value="python">

```py
h3.get_base_cell_number(h)
```

</TabItem>
<TabItem value="go">

```go
cell.BaseCellNumber()
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_get_base_cell_number(h)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 getBaseCellNumber --help
h3: Extracts the base cell number (0 - 121) from the H3 cell
H3 4.1.0

	getBaseCellNumber	Extracts the base cell number (0 - 121) from the H3 cell
	-h, --help	Show this help message.
	-c, --cell <index>	Required. H3 Cell
```

```bash
$ h3 getBaseCellNumber -c 85283473fffffff
20
```

</TabItem>
</Tabs>

## getIndexDigit

Returns an [indexing digit](https://h3geo.org/docs/library/index/cell) of the index.
Works for cells, edges and vertexes.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
// {label: 'Java', value: 'java'},
// {label: 'JavaScript (Live)', value: 'javascript'},
// {label: 'Python', value: 'python'},
// {label: 'Go', value: 'go'},
// {label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error getIndexDigit(H3Index h, int res, H3Index *out);
```

</TabItem>
<TabItem value="java">

```java
int getIndexDigit(long h3, int res);
int getIndexDigit(String h3Address, int res);
```

</TabItem>
<TabItem value="javascript">

```js
h3.getIndexDigit(h, res);
```

```js live
function example() {
  const h = "85283473fffffff";
  const res = 2;
  return h3.getIndexDigit(h, res);
}
```

</TabItem>
<TabItem value="python">

```py
h3.get_index_digit(h, res)
```

</TabItem>
<TabItem value="go">

```go
cell.IndexDigit(res)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_get_index_digit(h, res)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 getIndexDigit --help
h3: Extracts the indexing digit (0 - 7) from the H3 cell
H3 4.3.0

	getIndexDigit	Extracts the indexing digit (0 - 7) from the H3 cell
	-h, --help	Show this help message.
	-c, --cell <index>	Required. H3 Cell
	-r, --res <res>	Required. Indexing resolution (1 - 15)
```

```bash
$ h3 getIndexDigit -c 85283473fffffff -r 2
7
```

</TabItem>
</Tabs>

Digits are 1-indexed starting with the resolution 1 digit.

This function will return unused index digits as well as used ones,
in that case they will be 7 for valid cells.

## constructCell

Creates a cell from its components (resolution, base cell number, and indexing digits).
This is the inverse operation of `getResolution`, `getBaseCellNumber`, and `getIndexDigit`.
Only allows for constructing valid H3 cells, and will return an error if the provided components would create an invalid cell.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error constructCell(int res, int baseCellNumber, const int *digits, H3Index *out);
```

- `res`: Resolution (0-15)
- `baseCellNumber`: Base cell number (0-121)
- `digits`: Array of indexing digits (0-6) of length `res`. Each digit `digits[i]` corresponds to the digit at resolution `i+1`. Can be `NULL` if `res` is 0.
- `out`: Output parameter for the constructed cell

Returns 0 (`E_SUCCESS`) on success. Returns an error code on failure:

- `E_RES_DOMAIN`: Invalid resolution (must be 0-15)
- `E_BASE_CELL_DOMAIN`: Invalid base cell number (must be 0-121)
- `E_DIGIT_DOMAIN`: Invalid digit value (must be 0-6)
- `E_DELETED_DIGIT`: Attempted to use digit 1 in a pentagon base cell (deleted subsequence)

</TabItem>
<TabItem value="java">

```java
long constructCell(int baseCellNumber, List<Integer> digits);
long constructCell(int baseCellNumber, List<Integer> digits, int res);
String constructCellAddress(int baseCellNumber, List<Integer> digits);
String constructCellAddress(int baseCellNumber, List<Integer> digits, int res);
```

</TabItem>
<TabItem value="javascript">

```js
h3.constructCell(baseCellNumber, digits);
h3.constructCell(baseCellNumber, digits, res);
```

```js live
function example() {
  const baseCellNumber = 0;
  const res = 1;
  return h3.constructCell(baseCellNumber, [0], res);
}
```

</TabItem>
<TabItem value="python">

:::note

This function may not be available in all bindings.

:::

</TabItem>
<TabItem value="go">

:::note

This function may not be available in all bindings.

:::

</TabItem>
<TabItem value="duckdb">

```sql
h3_construct_cell(base_cell_number, digits)
h3_construct_cell(base_cell_number, digits, res)
h3_construct_cell_string(base_cell_number, digits)
h3_construct_cell_string(base_cell_number, digits, res)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 constructCell --help
H3 4.3.0

    constructCell   Construct an H3 cell from resolution, base cell, and digits
    -h, --help      Show this help message.
    -r, --resolution <res>  Resolution, 0-15 inclusive. Inferred from digits if not provided. If provided, an error will be returned if there is a mismatch with the number of digits provided.
    -b, --baseCell <base>   Required. Base cell number, 0-121 inclusive.
    -d, --digits <d0,d1,...>        Comma-separated list of child digits (0-6) of length resolution.
    -f, --format <FMT>      'json' for "CELL"\n, 'newline' for CELL\n (Default: json)
```

```bash
$ h3 constructCell -r 3 -b 73 -d 1,2,3
"839253fffffffff"
```

</TabItem>
</Tabs>

:::note

When constructing a cell from a pentagon base cell, digit `1` (K_AXES_DIGIT) is not allowed to follow immediately after a sequence of `0` digits. In this case, the function will return `E_DELETED_DIGIT`.

:::

## stringToH3

Converts the string representation to `H3Index` (`uint64_t`) representation.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error stringToH3(const char *str, H3Index *out);
```

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
long stringToH3(String h3Address);
```

</TabItem>
<TabItem value="javascript">

:::note

The H3 JavaScript binding supports only the string representation of an H3 index.

:::

</TabItem>
<TabItem value="python">

```py
h3.str_to_int(h)
```

</TabItem>
<TabItem value="go">

```go
h3.IndexFromString(str)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_string_to_h3(h)
```

</TabItem>
<TabItem value="shell">

:::note

The H3 CLI supports only the string representation of an H3 index.

:::

</TabItem>
</Tabs>

## h3ToString

Converts the `H3Index` representation of the index to the string representation.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error h3ToString(H3Index h, char *str, size_t sz);
```

`str` must be at least of length 17.
Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
String h3ToString(long h3);
```

</TabItem>
<TabItem value="javascript">

:::note

The H3 JavaScript binding supports only the string representation of an H3 index.

:::

</TabItem>
<TabItem value="python">

```py
h3.int_to_str(h)
```

</TabItem>
<TabItem value="go">

```go
cell.String()
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_h3_to_string(h)
```

</TabItem>
<TabItem value="shell">

:::note

The H3 CLI supports only the string representation of an H3 index.

:::

</TabItem>
</Tabs>

## isValidCell

Returns non-zero if this is a valid H3 cell index.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
int isValidCell(H3Index h);
```

</TabItem>
<TabItem value="java">

```java
boolean isValidCell(long h3);
boolean isValidCell(String h3Address);
```

</TabItem>
<TabItem value="javascript">

```js
h3.isValidCell(h);
```

```js live
function example() {
  const h = "85283473fffffff";
  return h3.isValidCell(h);
}
```

</TabItem>
<TabItem value="python">

```py
h3.is_valid_cell(h)
```

</TabItem>
<TabItem value="go">

```go
cell.IsValid()
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_is_valid_cell(h)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 isValidCell --help
h3: Checks if the provided H3 index is actually valid
H3 4.1.0

	isValidCell	Checks if the provided H3 index is actually valid
	-h, --help	Show this help message.
	-c, --cell <index>	Required. H3 Cell
	-f, --format <FMT>	'json' for true or false, 'numeric' for 1 or 0 (Default: json)
```

```bash
$ h3 isValidCell -c 85283473fffffff
true
```

</TabItem>
</Tabs>

## isValidIndex

Returns non-zero if this is a valid H3 index for any mode (cell, directed edge, or vertex).
That is, this returns true if any of the functions `isValidCell`, `isValidDirectedEdge`, or `isValidVertex` would return true.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
int isValidIndex(H3Index h);
```

Returns 1 if the H3 index is valid for any supported type (cell, directed edge, or vertex), 0 otherwise.

</TabItem>
<TabItem value="java">

```java
boolean isValidIndex(long h3);
boolean isValidIndex(String h3Address);
```

</TabItem>
<TabItem value="javascript">

:::note

This function may not be available in all bindings.

:::

</TabItem>
<TabItem value="python">

:::note

This function may not be available in all bindings.

:::

</TabItem>
<TabItem value="go">

:::note

This function may not be available in all bindings.

:::

</TabItem>
<TabItem value="duckdb">

```sql
h3_is_valid_index(h)
```

</TabItem>
</Tabs>

## isResClassIII

Returns non-zero if this index has a resolution with Class III orientation.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
int isResClassIII(H3Index h);
```

</TabItem>
<TabItem value="java">

```java
boolean isResClassIII(long h3);
boolean isResClassIII(String h3Address);
```

</TabItem>
<TabItem value="javascript">

```js
h3.isResClassIII(h);
```

```js live
function example() {
  const h = "85283473fffffff";
  return h3.isResClassIII(h);
}
```

</TabItem>
<TabItem value="python">

```py
h3.is_res_class_III(h)
```

</TabItem>
<TabItem value="go">

```go
cell.IsResClassIII()
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_is_res_class_iii(h)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 isResClassIII --help
h3: Checks if the provided H3 index has a Class III orientation
H3 4.1.0

	isResClassIII	Checks if the provided H3 index has a Class III orientation
	-h, --help	Show this help message.
	-c, --cell <index>	Required. H3 Cell
	-f, --format <FMT>	'json' for true or false, 'numeric' for 1 or 0 (Default: json)
```

```bash
$ h3 isResClassIII -c 85283473fffffff
true
```

</TabItem>
</Tabs>

## isPentagon

Returns non-zero if this index represents a pentagonal cell.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
int isPentagon(H3Index h);
```

</TabItem>
<TabItem value="java">

```java
boolean isPentagon(long h3);
boolean isPentagon(String h3Address);
```

</TabItem>
<TabItem value="javascript">

```js
h3.isPentagon(h);
```

```js live
function example() {
  const h = "85283473fffffff";
  return h3.isPentagon(h);
}
```

</TabItem>
<TabItem value="python">

```py
h3.is_pentagon(h)
```

</TabItem>
<TabItem value="go">

```go
cell.IsPentagon()
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_is_pentagon(h)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 isPentagon --help
h3: Checks if the provided H3 index is a pentagon instead of a hexagon
H3 4.1.0

	isPentagon	Checks if the provided H3 index is a pentagon instead of a hexagon
	-h, --help	Show this help message.
	-c, --cell <index>	Required. H3 Cell
	-f, --format <FMT>	'json' for true or false, 'numeric' for 1 or 0 (Default: json)
```

```bash
$ h3 isPentagon -c 85283473fffffff
false
```

</TabItem>
</Tabs>

## getIcosahedronFaces

Find all icosahedron faces intersected by a given H3 cell.
Faces are represented as integers from 0-19, inclusive.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error getIcosahedronFaces(H3Index h, int* out);
```

Face values are placed in the array `out`.
`out` must be at least length of `maxFaceCount(h)`.
The array is sparse, and empty (no intersection) array values are represented by -1.

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
Collection<Integer> getIcosahedronFaces(long h3);
Collection<Integer> getIcosahedronFaces(String h3Address);
```

</TabItem>
<TabItem value="javascript">

```js
h3.getIcosahedronFaces(h);
```

```js live
function example() {
  const h = "85283473fffffff";
  return h3.getIcosahedronFaces(h);
}
```

</TabItem>
<TabItem value="python">

```py
h3.get_icosahedron_faces(h)
```

</TabItem>
<TabItem value="go">

```go
cell.IcosahedronFaces()
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_get_icosahedron_faces(h)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 getIcosahedronFaces --help
h3: Returns the icosahedron face numbers (0 - 19) that the H3 index intersects
H3 4.1.0

	getIcosahedronFaces	Returns the icosahedron face numbers (0 - 19) that the H3 index intersects
	-h, --help	Show this help message.
	-c, --cell <index>	Required. H3 Cell
	-f, --format <FMT>	'json' for [faceNum, ...], 'newline' for faceNum\n... (Default: json)
```

```bash
$ h3 getIcosahedronFaces -c 85283473fffffff
[7]
```

</TabItem>
</Tabs>

## maxFaceCount

Returns the maximum number of icosahedron faces the given H3 index may intersect.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error maxFaceCount(H3Index h3, int *out);
```

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="javascript">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="python">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="go">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="duckdb">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="shell">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
</Tabs>

# === api/misc ===

---

id: misc
title: Miscellaneous H3 functions
sidebar_label: Miscellaneous
slug: /api/misc

---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

These functions include descriptions of the H3 grid system.

## degsToRads

Converts degrees to radians.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
double degsToRads(double degrees);
```

</TabItem>
<TabItem value="java">

:::note

Use `java.lang.Math.toRadians(double degrees)` instead.

:::

</TabItem>
<TabItem value="javascript">

```js
h3.degsToRads(degrees);
```

```js live
function example() {
  const degrees = 45;
  return h3.degsToRads(degrees);
}
```

</TabItem>
<TabItem value="python">

:::note

Use `math.radians(degrees)` instead.

:::

</TabItem>
<TabItem value="go">

```go
degrees * h3.DegsToRads
```

</TabItem>
<TabItem value="duckdb">

:::note

Use `radians(degrees)` instead.

:::

</TabItem>
<TabItem value="shell">

```sh
$ h3 degsToRads --help
h3: Converts degrees to radians
H3 4.1.0

	degsToRads	Converts degrees to radians
	-d, --degree <DEG>	Required. Angle in degrees
	-h, --help	Show this help message.
```

```bash
$ h3 degsToRads -d 180
3.1415926536
```

</TabItem>
</Tabs>

## radsToDegs

Converts radians to degrees.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
double radsToDegs(double radians);
```

</TabItem>
<TabItem value="java">

:::note

Use `java.lang.Math.toDegrees(double radians)` instead.

:::

</TabItem>
<TabItem value="javascript">

```js
h3.radsToDegs(h);
```

```js live
function example() {
  const radians = 3.14159;
  return h3.radsToDegs(radians);
}
```

</TabItem>
<TabItem value="python">

:::note

Use `math.degrees(radians)` instead.

:::

</TabItem>
<TabItem value="go">

```go
radians * h3.RadsToDegs
```

</TabItem>
<TabItem value="duckdb">

:::note

Use `degrees(radians)` instead.

:::

</TabItem>
<TabItem value="shell">

```sh
$ h3 radsToDegs --help
h3: Converts radians to degrees
H3 4.1.0

	radsToDegs	Converts radians to degrees
	-r, --radian <RAD>	Required. Angle in radians
	-h, --help	Show this help message.
```

```bash
$ h3 radsToDegs -r 1
57.2957795131
```

</TabItem>
</Tabs>

## getHexagonAreaAvgKm2

Average hexagon area in square kilometers at the given resolution.
Excludes pentagons.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error getHexagonAreaAvgKm2(int res, double *out);
```

</TabItem>
<TabItem value="java">

```java
double getHexagonAreaAvg(int res, AreaUnit unit);
```

</TabItem>
<TabItem value="javascript">

```js
h3.getHexagonAreaAvg(res, h3.UNITS.km2);
```

```js live
function example() {
  const res = 5;
  return h3.getHexagonAreaAvg(res, h3.UNITS.km2);
}
```

</TabItem>
<TabItem value="python">

```py
h3.average_hexagon_area(res, unit='km^2')
```

</TabItem>
<TabItem value="go">

```go
h3.HexagonAreaAvgKm2(res)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_average_hexagon_area(res, 'km^2')
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 getHexagonAreaAvgKm2 --help
h3: The average area in square kilometers for a hexagon of a given resolution (excludes pentagons)
H3 4.1.0

	getHexagonAreaAvgKm2	The average area in square kilometers for a hexagon of a given resolution (excludes pentagons)
	-r, --resolution <res>	Required. Resolution, 0-15 inclusive.
	-h, --help	Show this help message.
```

```bash
$ h3 getHexagonAreaAvgKm2 -r 1
609788.4417941332
```

</TabItem>
</Tabs>

## getHexagonAreaAvgM2

Average hexagon area in square meters at the given resolution.
Excludes pentagons.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error getHexagonAreaAvgM2(int res, double *out);
```

</TabItem>
<TabItem value="java">

```java
double getHexagonAreaAvg(int res, AreaUnit unit);
```

</TabItem>
<TabItem value="javascript">

```js
h3.getHexagonAreaAvg(res, h3.UNITS.m2);
```

```js live
function example() {
  const res = 5;
  return h3.getHexagonAreaAvg(res, h3.UNITS.m2);
}
```

</TabItem>
<TabItem value="python">

```py
h3.average_hexagon_area(res, unit='m^2')
```

</TabItem>
<TabItem value="go">

```go
h3.HexagonAreaAvgM2(res)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_average_hexagon_area(res, 'm^2')
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 getHexagonAreaAvgM2 --help
h3: The average area in square meters for a hexagon of a given resolution (excludes pentagons)
H3 4.1.0

	getHexagonAreaAvgM2	The average area in square meters for a hexagon of a given resolution (excludes pentagons)
	-r, --resolution <res>	Required. Resolution, 0-15 inclusive.
	-h, --help	Show this help message.
```

```bash
$ h3 getHexagonAreaAvgM2 -r 5
252903858.1819452047
```

</TabItem>
</Tabs>

## cellAreaRads2

Exact area of specific cell in square radians.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error cellAreaRads2(H3Index h, double *out);
```

</TabItem>
<TabItem value="java">

```java
double cellArea(long h3, AreaUnit unit);
int cellArea(String h3Address, AreaUnit unit);
```

</TabItem>
<TabItem value="javascript">

```js
h3.cellArea(h, h3.UNITS.rads2);
```

```js live
function example() {
  const h = "85283473fffffff";
  return h3.cellArea(h, h3.UNITS.rads2);
}
```

</TabItem>
<TabItem value="python">

```py
h3.cell_area(h, unit='rads^2')
```

</TabItem>
<TabItem value="go">

```go
h3.CellAreaRads2(cell)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_cell_area(h, 'rads^2')
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 cellAreaRads2 --help
h3: The exact area of a specific cell in square radians
H3 4.1.0

	cellAreaRads2	The exact area of a specific cell in square radians
	-c, --cell <index>	Required. H3 Cell
	-h, --help	Show this help message.
```

```bash
$ h3 cellAreaRads2 -c 85283473fffffff
0.0000065310
```

</TabItem>
</Tabs>

## cellAreaKm2

Exact area of specific cell in square kilometers.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error cellAreaKm2(H3Index h, double *out);
```

</TabItem>
<TabItem value="java">

```java
double cellArea(long h3, AreaUnit unit);
int cellArea(String h3Address, AreaUnit unit);
```

</TabItem>
<TabItem value="javascript">

```js
h3.cellArea(h, h3.UNITS.km2);
```

```js live
function example() {
  const h = "85283473fffffff";
  return h3.cellArea(h, h3.UNITS.km2);
}
```

</TabItem>
<TabItem value="python">

```py
h3.cell_area(h, unit='km^2')
```

</TabItem>
<TabItem value="go">

```go
h3.CellAreaKm2(cell)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_cell_area(h, 'km^2')
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 cellAreaKm2 --help
h3: The exact area of a specific cell in square kilometers
H3 4.1.0

	cellAreaKm2	The exact area of a specific cell in square kilometers
	-c, --cell <index>	Required. H3 Cell
	-h, --help	Show this help message.
```

```bash
$ h3 cellAreaKm2 -c 85283473fffffff
265.0925581283
```

</TabItem>
</Tabs>

## cellAreaM2

Exact area of specific cell in square meters.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error cellAreaM2(H3Index h, double *out);
```

</TabItem>
<TabItem value="java">

```java
double cellArea(long h3, AreaUnit unit);
int cellArea(String h3Address, AreaUnit unit);
```

</TabItem>
<TabItem value="javascript">

```js
h3.cellArea(h, h3.UNITS.m2);
```

```js live
function example() {
  const h = "85283473fffffff";
  return h3.cellArea(h, h3.UNITS.m2);
}
```

</TabItem>
<TabItem value="python">

```py
h3.cell_area(h, unit='m^2')
```

</TabItem>
<TabItem value="go">

```go
h3.CellAreaM2(cell)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_cell_area(h, 'm^2')
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 cellAreaM2 --help
h3: The exact area of a specific cell in square meters
H3 4.1.0

	cellAreaM2	The exact area of a specific cell in square meters
	-c, --cell <index>	Required. H3 Cell
	-h, --help	Show this help message.
```

```bash
$ h3 cellAreaM2 -c 85283473fffffff
265092558.1282823086
```

</TabItem>
</Tabs>

## getHexagonEdgeLengthAvgKm

Average hexagon edge length in kilometers at the given resolution.
Excludes pentagons.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error getHexagonEdgeLengthAvgKm(int res, double *out);
```

</TabItem>
<TabItem value="java">

```java
double getHexagonEdgeLengthAvg(int res, LengthUnit unit);
```

</TabItem>
<TabItem value="javascript">

```js
h3.getHexagonEdgeLengthAvg(res, h3.UNITS.km);
```

```js live
function example() {
  const res = 5;
  return h3.getHexagonEdgeLengthAvg(res, h3.UNITS.km);
}
```

</TabItem>
<TabItem value="python">

```py
h3.average_hexagon_edge_length(res, unit='km')
```

</TabItem>
<TabItem value="go">

```go
h3.HexagonEdgeLengthAvgKm(res)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_average_hexagon_edge_length(res, 'km')
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 getHexagonEdgeLengthAvgKm --help
h3: The average hexagon edge length in kilometers of a given resolution (excludes pentagons)
H3 4.1.0

	getHexagonEdgeLengthAvgKm	The average hexagon edge length in kilometers of a given resolution (excludes pentagons)
	-r, --resolution <res>	Required. Resolution, 0-15 inclusive.
	-h, --help	Show this help message.
```

```bash
$ h3 getHexagonEdgeLengthAvgKm -r 5
9.8540909900
```

</TabItem>
</Tabs>

## getHexagonEdgeLengthAvgM

Average hexagon edge length in meters at the given resolution.
Excludes pentagons.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error getHexagonEdgeLengthAvgM(int res, double *out);
```

</TabItem>
<TabItem value="java">

```java
double getHexagonEdgeLengthAvg(int res, LengthUnit unit);
```

</TabItem>
<TabItem value="javascript">

```js
h3.getHexagonEdgeLengthAvg(res, h3.UNITS.m);
```

```js live
function example() {
  const res = 5;
  return h3.getHexagonEdgeLengthAvg(res, h3.UNITS.m);
}
```

</TabItem>
<TabItem value="python">

```py
h3.average_hexagon_edge_length(res, unit='m')
```

</TabItem>
<TabItem value="go">

```go
h3.HexagonEdgeLengthAvgM(res)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_average_hexagon_edge_length(res, 'm')
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 getHexagonEdgeLengthAvgM --help
h3: The average hexagon edge length in meters of a given resolution (excludes pentagons)
H3 4.1.0

	getHexagonEdgeLengthAvgM	The average hexagon edge length in meters of a given resolution (excludes pentagons)
	-r, --resolution <res>	Required. Resolution, 0-15 inclusive.
	-h, --help	Show this help message.
```

```bash
$ h3 getHexagonEdgeLengthAvgM -r 5
9854.0909900000
```

</TabItem>
</Tabs>

## edgeLengthKm

Exact edge length of specific unidirectional edge in kilometers.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error edgeLengthKm(H3Index edge, double *length);
```

</TabItem>
<TabItem value="java">

```java
double edgeLength(long h3, LengthUnit unit);
double edgeLength(String h3Address, LengthUnit unit);
```

</TabItem>
<TabItem value="javascript">

```js
h3.edgeLength(h3, h3.UNITS.km);
```

```js live
function example() {
  const h = "115283473fffffff";
  return h3.edgeLength(h, h3.UNITS.km);
}
```

</TabItem>
<TabItem value="python">

```py
h3.edge_length(h, unit='km')
```

</TabItem>
<TabItem value="go">

```go
h3.EdgeLengthKm(edge)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_edge_length(h, 'km')
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 edgeLengthKm --help
h3: The exact edge length of a specific directed edge in kilometers
H3 4.1.0

	edgeLengthKm	The exact edge length of a specific directed edge in kilometers
	-c, --cell <index>	Required. H3 Cell
	-h, --help	Show this help message.
```

```bash
$ h3 edgeLengthKm -c 115283473fffffff
10.2947360862
```

</TabItem>
</Tabs>

## edgeLengthM

Exact edge length of specific unidirectional edge in meters.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error edgeLengthM(H3Index edge, double *length);
```

</TabItem>
<TabItem value="java">

```java
double edgeLength(long h3, LengthUnit unit);
double edgeLength(String h3Address, LengthUnit unit);
```

</TabItem>
<TabItem value="javascript">

```js
h3.edgeLength(h3, h3.UNITS.m);
```

```js live
function example() {
  const h = "115283473fffffff";
  return h3.edgeLength(h, h3.UNITS.m);
}
```

</TabItem>
<TabItem value="python">

```py
h3.edge_length(h, unit='m')
```

</TabItem>
<TabItem value="go">

```go
h3.EdgeLengthM(edge)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_edge_length(h, 'm')
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 edgeLengthM --help
h3: The exact edge length of a specific directed edge in meters
H3 4.1.0

	edgeLengthM	The exact edge length of a specific directed edge in meters
	-c, --cell <index>	Required. H3 Cell
	-h, --help	Show this help message.
```

```bash
$ h3 edgeLengthM -c 115283473fffffff
10294.7360861995
```

</TabItem>
</Tabs>

## edgeLengthRads

Exact edge length of specific unidirectional edge in radians.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error edgeLengthRads(H3Index edge, double *length);
```

</TabItem>
<TabItem value="java">

```java
double edgeLength(long h3, LengthUnit unit);
double edgeLength(String h3Address, LengthUnit unit);
```

</TabItem>
<TabItem value="javascript">

```js
h3.edgeLength(h3, h3.UNITS.rads);
```

```js live
function example() {
  const h = "115283473fffffff";
  return h3.edgeLength(h, h3.UNITS.rads);
}
```

</TabItem>
<TabItem value="python">

```py
h3.edge_length(h, unit='rads')
```

</TabItem>
<TabItem value="go">

```go
h3.EdgeLengthRads(edge)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_edge_length(h, 'rads')
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 edgeLengthRads --help
h3: The exact edge length of a specific directed edge in radians
H3 4.1.0

	edgeLengthRads	The exact edge length of a specific directed edge in radians
	-c, --cell <index>	Required. H3 Cell
	-h, --help	Show this help message.
```

```bash
$ h3 edgeLengthRads -c 115283473fffffff
0.0016158726
```

</TabItem>
</Tabs>

## getNumCells

Number of unique H3 indexes at the given resolution.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error getNumCells(int res, int64_t *out);
```

</TabItem>
<TabItem value="java">

```java
long getNumCells(int res);
```

</TabItem>
<TabItem value="javascript">

```js
h3.getNumCells(res);
```

```js live
function example() {
  const res = 5;
  return h3.getNumCells(res);
}
```

</TabItem>
<TabItem value="python">

```py
h3.get_num_cells(res)
```

</TabItem>
<TabItem value="go">

```go
h3.NumCells(res)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_get_num_cells(res)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 getNumCells --help
h3: The number of unique H3 cells for a specified resolution
H3 4.1.0

	getNumCells	The number of unique H3 cells for a specified resolution
	-r, --resolution <res>	Required. Resolution, 0-15 inclusive.
	-h, --help	Show this help message.
```

```bash
$ h3 getNumCells -r 5
2016842
```

</TabItem>
</Tabs>

## getRes0Cells

Provide all the resolution `0` H3 cells.
These are the coarsest cells that can be represented in the H3 system and are
the parents/ancestors of all other cells in the H3 grid system.
The returned cells correspond to the 122 base cells.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error getRes0Cells(H3Index *out);
```

`out` must be an array of at least size `res0CellCount()`.

</TabItem>
<TabItem value="java">

```java
Collection<Long> getRes0Cells();
Collection<String> getRes0CellAddresses();
```

</TabItem>
<TabItem value="javascript">

```js
h3.getRes0Cells();
```

```js live
function example() {
  return h3.getRes0Cells();
}
```

</TabItem>
<TabItem value="python">

```py
h3.get_res0_cells()
```

</TabItem>
<TabItem value="go">

```go
h3.Res0Cells()
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_get_res0_cells()
```

```sql
h3_get_res0_cells_string()
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 getRes0Cells --help
h3: Returns all of the resolution 0 cells
H3 4.1.0

	getRes0Cells	Returns all of the resolution 0 cells
	-h, --help	Show this help message.
	-f, --format <FMT>	'json' for ["CELL", ...], 'newline' for CELL\n... (Default: json)
```

```bash
$ h3 getRes0Cells
[ "8001fffffffffff", "8003fffffffffff", "8005fffffffffff", "8007fffffffffff", "8009fffffffffff", "800bfffffffffff", "800dfffffffffff", "800ffffffffffff", "8011fffffffffff", "8013fffffffffff", "8015fffffffffff", "8017fffffffffff", "8019fffffffffff", "801bfffffffffff", "801dfffffffffff", "801ffffffffffff", "8021fffffffffff", "8023fffffffffff", "8025fffffffffff", "8027fffffffffff", "8029fffffffffff", "802bfffffffffff", "802dfffffffffff", "802ffffffffffff", "8031fffffffffff", "8033fffffffffff", "8035fffffffffff", "8037fffffffffff", "8039fffffffffff", "803bfffffffffff", "803dfffffffffff", "803ffffffffffff", "8041fffffffffff", "8043fffffffffff", "8045fffffffffff", "8047fffffffffff", "8049fffffffffff", "804bfffffffffff", "804dfffffffffff", "804ffffffffffff", "8051fffffffffff", "8053fffffffffff", "8055fffffffffff", "8057fffffffffff", "8059fffffffffff", "805bfffffffffff", "805dfffffffffff", "805ffffffffffff", "8061fffffffffff", "8063fffffffffff", "8065fffffffffff", "8067fffffffffff", "8069fffffffffff", "806bfffffffffff", "806dfffffffffff", "806ffffffffffff", "8071fffffffffff", "8073fffffffffff", "8075fffffffffff", "8077fffffffffff", "8079fffffffffff", "807bfffffffffff", "807dfffffffffff", "807ffffffffffff", "8081fffffffffff", "8083fffffffffff", "8085fffffffffff", "8087fffffffffff", "8089fffffffffff", "808bfffffffffff", "808dfffffffffff", "808ffffffffffff", "8091fffffffffff", "8093fffffffffff", "8095fffffffffff", "8097fffffffffff", "8099fffffffffff", "809bfffffffffff", "809dfffffffffff", "809ffffffffffff", "80a1fffffffffff", "80a3fffffffffff", "80a5fffffffffff", "80a7fffffffffff", "80a9fffffffffff", "80abfffffffffff", "80adfffffffffff", "80affffffffffff", "80b1fffffffffff", "80b3fffffffffff", "80b5fffffffffff", "80b7fffffffffff", "80b9fffffffffff", "80bbfffffffffff", "80bdfffffffffff", "80bffffffffffff", "80c1fffffffffff", "80c3fffffffffff", "80c5fffffffffff", "80c7fffffffffff", "80c9fffffffffff", "80cbfffffffffff", "80cdfffffffffff", "80cffffffffffff", "80d1fffffffffff", "80d3fffffffffff", "80d5fffffffffff", "80d7fffffffffff", "80d9fffffffffff", "80dbfffffffffff", "80ddfffffffffff", "80dffffffffffff", "80e1fffffffffff", "80e3fffffffffff", "80e5fffffffffff", "80e7fffffffffff", "80e9fffffffffff", "80ebfffffffffff", "80edfffffffffff", "80effffffffffff", "80f1fffffffffff", "80f3fffffffffff" ]
```

</TabItem>
</Tabs>

## res0CellCount

Number of resolution `0` H3 indexes, which is defined as 122.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
int res0CellCount(void);
```

</TabItem>
<TabItem value="java">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="javascript">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="python">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="go">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="duckdb">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="shell">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
</Tabs>

## getPentagons

All the pentagon H3 cells at the specified resolution.
There are 12 pentagons at each resolution.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error getPentagons(int res, H3Index *out);
```

`out` must be an array of at least size `pentagonIndexCount()`.

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
Collection<Long> h3.getPentagons(int res);
Collection<String> h3.getPentagonsAddresses(int res);
```

</TabItem>
<TabItem value="javascript">

```js
h3.getPentagons(res);
```

```js live
function example() {
  const res = 5;
  return h3.getPentagons(res);
}
```

</TabItem>
<TabItem value="python">

```py
h3.get_pentagons(res)
```

</TabItem>
<TabItem value="go">

```go
h3.Pentagons(res)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_get_pentagons(res)
```

```sql
h3_get_pentagons_string(res)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 getPentagons --help
h3: Returns all of the pentagons at the specified resolution
H3 4.1.0

	getPentagons	Returns all of the pentagons at the specified resolution
	-r, --resolution <res>	Required. Resolution, 0-15 inclusive.
	-h, --help	Show this help message.
	-f, --format <FMT>	'json' for ["CELL", ...], 'newline' for CELL\n... (Default: json)
```

```bash
$ h3 getPentagons -r 5
[ "85080003fffffff", "851c0003fffffff", "85300003fffffff", "854c0003fffffff", "85620003fffffff", "85740003fffffff", "857e0003fffffff", "85900003fffffff", "85a60003fffffff", "85c20003fffffff", "85d60003fffffff", "85ea0003fffffff" ]
```

</TabItem>
</Tabs>

## pentagonCount

Number of pentagon H3 cells per resolution.
This is always 12, but provided as a convenience.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
int pentagonCount(void);
```

</TabItem>
<TabItem value="java">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="javascript">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="python">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="go">

```go
h3.NumPentagons
```

</TabItem>
<TabItem value="duckdb">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="shell">

```sh
$ h3 pentagonCount --help
h3: Returns 12
H3 4.1.0

	pentagonCount	Returns 12
	-h, --help	Show this help message.
```

```bash
$ h3 pentagonCount
12
```

</TabItem>
</Tabs>

## greatCircleDistanceKm

Gives the "great circle" or "haversine" distance between pairs of
LatLng points (lat/lng pairs) in kilometers.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
double greatCircleDistanceKm(const LatLng *a, const LatLng *b);
```

</TabItem>
<TabItem value="java">

```java
double greatCircleDistance(LatLng point1, LatLng point2, LengthUnit unit);
```

</TabItem>
<TabItem value="javascript">

```js
h3.greatCircleDistance(point1, point2, h3.UNITS.km);
```

```js live
function example() {
  const point1 = [-10, 0];
  const point2 = [10, 0];
  return h3.greatCircleDistance(point1, point2, h3.UNITS.km);
}
```

</TabItem>
<TabItem value="python">

```py
h3.great_circle_distance(point1, point2, unit='km')
```

</TabItem>
<TabItem value="go">

```go
h3.GreatCircleDistanceKm(h3.NewLatLng(latA, lngA), h3.NewLatLng(latB, lngB))
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_great_circle_distance(point1, point2, 'km')
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 greatCircleDistanceKm --help
h3: Calculates the 'great circle' or 'haversine' distance between two lat, lng points, in kilometers
H3 4.1.0

	greatCircleDistanceKm	Calculates the 'great circle' or 'haversine' distance between two lat, lng points, in kilometers
	-i, --file <FILENAME>	The file to load the coordinates from. Use -- to read from stdin.
	-c, --coordinates <ARRAY>	The array of coordinates to convert. Up to 1500 characters.
	-h, --help	Show this help message.
```

```bash
$ h3 greatCircleDistanceKm -c "[[-10, 0], [10, 0]]"
2223.9010395046
```

</TabItem>
</Tabs>

## greatCircleDistanceM

Gives the "great circle" or "haversine" distance between pairs of
LatLng points (lat/lng pairs) in meters.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
double greatCircleDistanceM(const LatLng *a, const LatLng *b);
```

</TabItem>
<TabItem value="java">

```java
double greatCircleDistance(LatLng point1, LatLng point2, LengthUnit unit);
```

</TabItem>
<TabItem value="javascript">

```js
h3.greatCircleDistance(point1, point2, h3.UNITS.m);
```

```js live
function example() {
  const point1 = [-10, 0];
  const point2 = [10, 0];
  return h3.greatCircleDistance(point1, point2, h3.UNITS.m);
}
```

</TabItem>
<TabItem value="python">

```py
h3.great_circle_distance(point1, point2, unit='m')
```

</TabItem>
<TabItem value="go">

```go
h3.GreatCircleDistanceM(h3.NewLatLng(latA, lngA), h3.NewLatLng(latB, lngB))
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_great_circle_distance(point1, point2, 'm')
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 greatCircleDistanceM --help
h3: Calculates the 'great circle' or 'haversine' distance between two lat, lng points, in meters
H3 4.1.0

	greatCircleDistanceM	Calculates the 'great circle' or 'haversine' distance between two lat, lng points, in meters
	-i, --file <FILENAME>	The file to load the coordinates from. Use -- to read from stdin.
	-c, --coordinates <ARRAY>	The array of coordinates to convert. Up to 1500 characters.
	-h, --help	Show this help message.
```

```bash
$ h3 greatCircleDistanceM -c "[[-10, 0], [10, 0]]"
2223901.0395045886
```

</TabItem>
</Tabs>

## greatCircleDistanceRads

Gives the "great circle" or "haversine" distance between pairs of
LatLng points (lat/lng pairs) in radians.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
double greatCircleDistanceRads(const LatLng *a, const LatLng *b);
```

</TabItem>
<TabItem value="java">

```java
double greatCircleDistance(LatLng point1, LatLng point2, LengthUnit unit);
```

</TabItem>
<TabItem value="javascript">

```js
h3.greatCircleDistance(point1, point2, h3.UNITS.rads);
```

```js live
function example() {
  const point1 = [-10, 0];
  const point2 = [10, 0];
  return h3.greatCircleDistance(point1, point2, h3.UNITS.rads);
}
```

</TabItem>
<TabItem value="python">

```py
h3.great_circle_distance(point1, point2, unit='rads')
```

</TabItem>
<TabItem value="go">

```go
h3.GreatCircleDistanceRads(h3.NewLatLng(latA, lngA), h3.NewLatLng(latB, lngB))
```

</TabItem>
<TabItem value="duckdb">

```sql
h3.great_circle_distance(point1, point2, 'rads')
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 greatCircleDistanceRads --help
h3: Calculates the 'great circle' or 'haversine' distance between two lat, lng points, in radians
H3 4.1.0

	greatCircleDistanceRads	Calculates the 'great circle' or 'haversine' distance between two lat, lng points, in radians
	-i, --file <FILENAME>	The file to load the coordinates from. Use -- to read from stdin.
	-c, --coordinates <ARRAY>	The array of coordinates to convert. Up to 1500 characters.
	-h, --help	Show this help message.
```

```bash
$ h3 greatCircleDistanceRads -c "[[-10, 0], [10, 0]]"
0.3490658504
```

</TabItem>
</Tabs>

## describeH3Error

Provides a human-readable description of an H3Error error code.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
char *describeH3Error(H3Error err);
```

This function cannot fail, as it just returns a string stating that the
H3Error value is itself invalid and does not allocate memory to do so.
Do not call `free` on the result of this function.

</TabItem>
<TabItem value="javascript">

:::note

Just read the `.message` property from the caught error, instead.

:::

```js live
function example() {
  let errorMessage = "";
  try {
    h3.cellToChildrenSize("asdf", 9);
  } catch (e) {
    errorMessage = e.message;
  }
  return errorMessage;
}
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 describeH3Error --help
h3: Returns a description of the provided H3 error code number, or indicates the number is itself invalid.
H3 4.1.0

	describeH3ErrorReturns a description of the provided H3 error code number, or indicates the number is itself invalid.
	-e, --error <CODE>	Required. H3 Error code to describe
	-h, --help	Show this help message.
```

```bash
$ h3 describeH3Error -e 5
Cell argument was not valid
```

</TabItem>
</Tabs>

# === api/regions ===

---

id: regions
title: Region functions
sidebar_label: Regions
slug: /api/regions

---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

These functions convert H3 indexes to and from polygonal areas.

## polygonToCells

Each binding's version of `polygonToCells` takes as input a GeoJSON-like data
structure describing a polygon (i.e., an outer ring and optional holes) and
a target cell resolution.
It produces a collection of cells that are contained within the polygon.

Containment is determined by centroids of the cells, so that a partitioning
of polygons (covering an area without overlaps) will result in
a partitioning of H3 cells.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error polygonToCells(const GeoPolygon *geoPolygon, int res, uint32_t flags, H3Index *out);
```

In C, `polygonToCells` takes a `GeoPolygon` struct and preallocated,
zeroed memory, and fills it with the covering cells.

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
List<Long> polygonToCells(List<LatLng> points, List<List<LatLng>> holes, int res);
List<String> polygonToCellAddresses(List<LatLng> points, List<List<LatLng>> holes, int res);
```

</TabItem>
<TabItem value="javascript">

```js
h3.polygonToCells(polygon, res, isGeoJson);
```

```js live
function example() {
  const polygon = [
    [37.813318999983238, -122.4089866999972145],
    [37.7198061999978478, -122.3544736999993603],
    [37.8151571999998453, -122.4798767000009008],
  ];
  const res = 7;
  return h3.polygonToCells(polygon, res);
}
```

</TabItem>
<TabItem value="python">

```py
h3.polygon_to_cells(h3shape, res)
h3.h3shape_to_cells(h3shape, res)
```

In Python, `h3shape_to_cells` takes an `H3Shape` object
(`LatLngPoly` or `LatLngMultiPoly`).
Note that `polygon_to_cells` is an alias for `h3shape_to_cells`.
For more info, see the [`h3-py` docs](https://uber.github.io/h3-py/api_quick.html#polygon-interface).

</TabItem>
<TabItem value="go">

```go
h3.PolygonToCells(polygon, res)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_polygon_wkt_to_cells(wkt, res)
```

```sql
h3_polygon_wkt_to_cells_string(wkt, res)
```

```sql
h3_polygon_wkb_to_cells(wkb, res)
```

```sql
h3_polygon_wkb_to_cells_string(wkb, res)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 polygonToCells --help
h3: Converts a polygon (array of lat, lng points, or array of arrays of lat, lng points) into a set of covering cells at the specified resolution
H3 4.1.0

	polygonToCells	Converts a polygon (array of lat, lng points, or array of arrays of lat, lng points) into a set of covering cells at the specified resolution
	-h, --help	Show this help message.
	-i, --file <FILENAME>	The file to load the polygon from. Use -- to read from stdin.
	-p, --polygon <POLYGON>	The polygon to convert. Up to 1500 characters.
	-r, --resolution <res>	Required. Resolution, 0-15 inclusive, that the polygon should be converted to.
	-f, --format <FMT>	'json' for ["CELL", ...], 'newline' for CELL\n... (Default: json)
```

```bash
$ h3 polygonToCells -r 7 -p "[[37.813318999983238, -122.4089866999972145], [37.7198061999978478, -122.3544736999993603], [37.8151571999998453, -122.4798767000009008]]"
[ "87283082bffffff", "872830870ffffff", "872830820ffffff", "87283082effffff", "872830828ffffff", "87283082affffff", "872830876ffffff" ]
```

</TabItem>
</Tabs>

## maxPolygonToCellsSize

Provides an upper bound on the number of cells needed for memory allocation
purposes when computing `polygonToCells` on the given GeoJSON-like data structure.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error maxPolygonToCellsSize(const GeoPolygon *geoPolygon, int res, uint32_t flags, int64_t *out);
```

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="javascript">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="python">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="go">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="duckdb">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="shell">

```sh
$ h3 maxPolygonToCellsSize --help
h3: Returns the maximum number of cells that could be needed to cover the polygon. Will always be equal or more than actually necessary
H3 4.1.0

	maxPolygonToCellsSize	Returns the maximum number of cells that could be needed to cover the polygon. Will always be equal or more than actually necessary
	-h, --help	Show this help message.
	-i, --file <FILENAME>	The file to load the polygon from. Use -- to read from stdin.
	-p, --polygon <POLYGON>	The polygon to convert. Up to 1500 characters.
	-r, --resolution <res>	Required. Resolution, 0-15 inclusive, that the polygon should be converted to.
```

```bash
$ h3 maxPolygonToCellsSize -r 7 -p "[[37.813318999983238, -122.4089866999972145], [37.7198061999978478, -122.3544736999993603], [37.8151571999998453, -122.4798767000009008]]"
100
```

</TabItem>
</Tabs>

## polygonToCellsExperimental

Each binding's version of `polygonToCellsExperimental` takes as input a
GeoJSON-like data structure describing a polygon (i.e., an outer ring and
optional holes) and a target cell resolution.
It produces a collection of cells that are contained within the polygon.

This function differs from `polygonToCells` in that it uses an experimental
new algorithm which supports center-based, fully-contained, and
overlapping containment modes.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error polygonToCellsExperimental(const GeoPolygon *geoPolygon, int res, uint32_t flags, int64_t size, H3Index *out);
```

In C, `polygonToCellsExperimental` takes a `GeoPolygon` struct and preallocated,
zeroed memory, and fills it with the covering cells.

`size` should be the size in number of `H3Index`s of `out`.

The valid values for `flags` are:

| Enum name                      | Integer value | Description                           |
| ------------------------------ | ------------- | ------------------------------------- |
| `CONTAINMENT_CENTER`           | 0             | Cell center is contained in the shape |
| `CONTAINMENT_FULL`             | 1             | Cell is fully contained in the shape  |
| `CONTAINMENT_OVERLAPPING`      | 2             | Cell overlaps the shape at any point  |
| `CONTAINMENT_OVERLAPPING_BBOX` | 3             | Cell bounding box overlaps shape      |

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
List<Long> polygonToCellsExperimental(List<LatLng> points, List<List<LatLng>> holes, PolygonToCellsFlags flags, int res);
List<String> polygonToCellExperimentalAddresses(List<LatLng> points, List<List<LatLng>> holes, PolygonToCellsFlags flags, int res);
```

The valid values for `flags` are:

| Enum name                                          | Description                           |
| -------------------------------------------------- | ------------------------------------- |
| `PolygonToCellsFlags.containment_center`           | Cell center is contained in the shape |
| `PolygonToCellsFlags.containment_full`             | Cell is fully contained in the shape  |
| `PolygonToCellsFlags.containment_overlapping`      | Cell overlaps the shape at any point  |
| `PolygonToCellsFlags.containment_overlapping_bbox` | Cell bounding box overlaps shape      |

</TabItem>
<TabItem value="javascript">

```js
h3.polygonToCellsExperimental(polygon, res, flags, isGeoJson);
```

```js live
function example() {
  const polygon = [
    [37.813318999983238, -122.4089866999972145],
    [37.7198061999978478, -122.3544736999993603],
    [37.8151571999998453, -122.4798767000009008],
  ];
  const res = 7;
  return h3.polygonToCellsExperimental(
    polygon,
    res,
    h3.POLYGON_TO_CELLS_FLAGS.containmentOverlapping,
  );
}
```

The valid values for `flags` are:

| Enum name                                             | Description                           |
| ----------------------------------------------------- | ------------------------------------- |
| `POLYGON_TO_CELLS_FLAGS.containment_center`           | Cell center is contained in the shape |
| `POLYGON_TO_CELLS_FLAGS.containment_full`             | Cell is fully contained in the shape  |
| `POLYGON_TO_CELLS_FLAGS.containment_overlapping`      | Cell overlaps the shape at any point  |
| `POLYGON_TO_CELLS_FLAGS.containment_overlapping_bbox` | Cell bounding box overlaps shape      |

</TabItem>
<TabItem value="python">

```py
h3.h3shape_to_cells_experimental(h3shape, res, contain='overlap')
```

In Python, `h3shape_to_cells_experimental` takes an `H3Shape` object
(`LatLngPoly` or `LatLngMultiPoly`).
For more info, see the [`h3-py` docs](https://uber.github.io/h3-py/api_quick.html#polygon-interface).

The valid values for `contain` are:

| String value   | Description                                     |
| -------------- | ----------------------------------------------- |
| `center`       | Cell center is contained in the shape (default) |
| `full`         | Cell is fully contained in the shape            |
| `overlap`      | Cell overlaps the shape at any point            |
| `bbox_overlap` | Cell bounding box overlaps shape                |

</TabItem>
<TabItem value="go">

```go
h3.PolygonToCellsExperimental(polygon, res, containmentMode, maxNumCellsReturn)
```

The valid values for `containmentMode` are:

| Enum name                       | Description                           |
| ------------------------------- | ------------------------------------- |
| `h3.ContainmentCenter`          | Cell center is contained in the shape |
| `h3.ContainmentFull`            | Cell is fully contained in the shape  |
| `h3.ContainmentOverlapping`     | Cell overlaps the shape at any point  |
| `h3.ContainmentOverlappingBbox` | Cell bounding box overlaps shape      |

</TabItem>
<TabItem value="duckdb">

```sql
h3_polygon_wkt_to_cells_experimental(wkt, res, 'overlap')
```

```sql
h3_polygon_wkt_to_cells_experimental_string(wkt, res, 'overlap')
```

```sql
h3_polygon_wkb_to_cells_experimental(wkb, res, 'overlap')
```

```sql
h3_polygon_wkb_to_cells_experimental_string(wkb, res, 'overlap')
```

The valid values for the third `contain` argument are:

| String value   | Description                                     |
| -------------- | ----------------------------------------------- |
| `center`       | Cell center is contained in the shape (default) |
| `full`         | Cell is fully contained in the shape            |
| `overlap`      | Cell overlaps the shape at any point            |
| `bbox_overlap` | Cell bounding box overlaps shape                |

</TabItem>
<TabItem value="shell">

This function is not exposed in the CLI bindings.

</TabItem>
</Tabs>

## maxPolygonToCellsSizeExperimental

Provides an upper bound on the number of cells needed for memory allocation
purposes when computing `polygonToCellsExperimental` on the given GeoJSON-like data structure.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error maxPolygonToCellsSizeExperimental(const GeoPolygon *geoPolygon, int res, uint32_t flags, int64_t *out);
```

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="javascript">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="python">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="go">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="duckdb">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="shell">

This function is not exposed in the CLI bindings.

</TabItem>
</Tabs>

## cellsToLinkedMultiPolygon / cellsToMultiPolygon

Create a GeoJSON-like multi-polygon describing the outline(s) of a set of cells.
Polygon outlines will follow GeoJSON MultiPolygon order: Each polygon will
have one outer loop, which is first in the list, followed by any holes.

It is expected that all cells in the set have the same resolution and
that the set contains no duplicates. Behavior is undefined if duplicates
or multiple resolutions are present, and the algorithm may produce
unexpected or invalid output.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error cellsToLinkedMultiPolygon(const H3Index *h3Set, const int numHexes, LinkedGeoPolygon *out);
```

It is the responsibility of the caller to call `destroyLinkedPolygon` on the
populated linked geo structure, or the memory for that structure will
not be freed.

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
List<List<List<LatLng>>> cellsToMultiPolygon(Collection<Long> h3, boolean geoJson);
List<List<List<LatLng>>> cellAddressesToMultiPolygon(Collection<String> h3Addresses, boolean geoJson);
```

</TabItem>
<TabItem value="javascript">

```js
h3.cellsToMultiPolygon(cells, geoJson);
```

```js live
function example() {
  const cells = ["872830828ffffff", "87283082effffff"];
  return h3.cellsToMultiPolygon(cells, true);
}
```

</TabItem>
<TabItem value="python">

```py
h3.cells_to_h3shape(cells, *, tight=True)
```

Returns an `H3Shape` object:

- If `tight=True`, returns `LatLngPoly` if possible, otherwise `LatLngMultiPoly`.
- If `tight=False`, always returns a `LatLngMultiPoly`.

For more info, see the [`h3-py` docs](https://uber.github.io/h3-py/api_quick.html#polygon-interface).

</TabItem>
<TabItem value="go">

```go
h3.CellsToMultiPolygon(cells)

```

</TabItem>
<TabItem value="duckdb">

```sql
h3_cells_to_multi_polygon_wkt(cells)
```

```sql
h3_cells_to_multi_polygon_wkb(cells)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 cellsToMultiPolygon --help
h3: Returns a polygon (array of arrays of lat, lng points) for a set of cells
H3 4.1.0

	cellsToMultiPolygon	Returns a polygon (array of arrays of lat, lng points) for a set of cells
	-h, --help	Show this help message.
	-i, --file <FILENAME>	The file to load the cells from. Use -- to read from stdin.
	-c, --cells <CELLS>	The cells to convert. Up to 100 cells if provided as hexadecimals with zero padding.
	-f, --format <FMT>	'json' for [[[[lat, lng],...],...],...] 'wkt' for a WKT MULTIPOLYGON
```

```bash
$ h3 cellsToMultiPolygon -c 872830828ffffff,87283082effffff
[[[[37.784046, -122.427089], [37.772267, -122.434586], [37.761736, -122.425769], [37.762982, -122.409455], [37.752446, -122.400640], [37.753689, -122.384324], [37.765468, -122.376819], [37.776004, -122.385635], [37.774761, -122.401954], [37.785293, -122.410771]]]]
```

</TabItem>
</Tabs>

## destroyLinkedMultiPolygon

Free all allocated memory for a linked geo structure. The caller is
responsible for freeing memory allocated to the input polygon struct.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
void destroyLinkedMultiPolygon(LinkedGeoPolygon *polygon);
```

</TabItem>
<TabItem value="java">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="javascript">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="python">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="go">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="duckdb">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="shell">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
</Tabs>

# === api/traversal ===

---

id: traversal
title: Grid traversal functions
sidebar_label: Traversal
slug: /api/traversal

---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

Grid traversal allows finding cells in the vicinity of an origin cell,
and determining how to traverse the grid from one cell to another.

## gridDistance

Provides the _grid distance_ between two cells, which is
defined as the minimum number of "hops" needed across adjacent cells to get
from one cell to the other.

Note that finding the grid distance may fail for a few reasons:

- the cells are not comparable (different resolutions),
- the cells are too far apart, or
- the cells are separated by pentagonal distortion.

This is the same set of limitations as the local IJ coordinate space functions.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error gridDistance(H3Index origin, H3Index h3, int64_t *distance);
```

Returns 0 (`E_SUCCESS`) on success, or an error if finding the distance failed.

</TabItem>
<TabItem value="java">

```java
long gridDistance(long a, long b) throws DistanceUndefinedException;
long gridDistance(String a, String b) throws DistanceUndefinedException;
```

</TabItem>
<TabItem value="javascript">

```js
h3.gridDistance(a, b);
```

```js live
function example() {
  const start = "85283473fffffff";
  const end = "8528342bfffffff";
  return h3.gridDistance(start, end);
}
```

</TabItem>
<TabItem value="python">

```py
h3.grid_distance(h1, h2)
```

</TabItem>
<TabItem value="go">

```go
cell.GridDistance(other)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_grid_distance(h1, h2)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 gridDistance --help
h3: Returns the number of steps along the grid to move from the origin cell to the destination cell
H3 4.1.0

  gridDistance  Returns the number of steps along the grid to move from the origin cell to the destination cell
  -h, --help  Show this help message.
  -o, --origin <cell> Required. The origin H3 cell
  -d, --destination <cell>  Required. The destination H3 cell
```

```bash
$ h3 gridDistance -o 85283473fffffff -d 8528342bfffffff
2
```

</TabItem>
</Tabs>

## gridRing

Produces the "hollow ring" of cells which are _exactly_ grid distance `k`
from the origin cell.

If pentagon distortion is encountered, this function will use a more memory-intensive
approach than `gridRingUnsafe` in order to compute the ring.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error gridRing(H3Index origin, int k, H3Index* out);
```

The caller should allocate memory for the maximum size of the ring, which is
given by `maxGridRingSize`. If fewer than the maximum number of cells are
generated, elements in `out` may be left zero.

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
List<Long> gridRing(long h3, int k);
List<String> gridRing(String h3Address, int k);
```

</TabItem>
<TabItem value="javascript">

```js
h3.gridRing(h3Index, k);
```

```js live
function example() {
  const h = "85283473fffffff";
  const k = 1;
  return h3.gridRing(h, k);
}
```

</TabItem>
<TabItem value="python">

```py
h3.grid_ring(h, k)
```

</TabItem>
<TabItem value="go">

```go
cell.GridRing(k)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_grid_ring(h, k)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 gridRing --help
h3: Returns an array of H3 cells, each cell 'k' steps away from the origin cell
H3 4.1.0

  gridRing  Returns an array of H3 cells, each cell 'k' steps away from the origin cell
  -h, --help  Show this help message.
  -c, --cell <index>  Required. H3 Cell
  -k <distance> Required. Maximum grid distance for the output set
  -f, --format <FMT>  'json' for ["CELL", ...], 'newline' for CELL\n... (Default: json)
```

```bash
$ h3 gridRing -k 1 -c 85283473fffffff
[ "8528340bfffffff", "85283447fffffff", "8528347bfffffff", "85283463fffffff", "85283477fffffff", "8528340ffffffff" ]
```

</TabItem>
</Tabs>

## gridRingUnsafe

Produces the "hollow ring" of cells which are _exactly_ grid distance `k`
from the origin cell.

This function may fail if pentagonal distortion is encountered.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error gridRingUnsafe(H3Index origin, int k, H3Index* out);
```

The caller should allocate memory for the maximum size of the ring, which is
given by `maxGridRingSize`.

Returns 0 (`E_SUCCESS`) if no pentagonal distortion was encountered.

</TabItem>
<TabItem value="java">

```java
List<Long> gridRingUnsafe(long h3, int k) throws PentagonEncounteredException;
List<String> gridRingUnsafe(String h3Address, int k) throws PentagonEncounteredException;
```

</TabItem>
<TabItem value="javascript">

```js
h3.gridRingUnsafe(h3Index, k);
```

```js live
function example() {
  const h = "85283473fffffff";
  const k = 1;
  return h3.gridRingUnsafe(h, k);
}
```

</TabItem>
<TabItem value="python">

:::note

This function is not exposed.

:::

</TabItem>
<TabItem value="go">

```go
cell.GridRingUnsafe(k)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_grid_ring_unsafe(h, k)
```

</TabItem>
<TabItem value="shell">

:::note

This function is not exposed.

:::

</TabItem>
</Tabs>

## maxGridRingSize

This function provides the maximum number of cells in the grid that are _exactly_
grid distance `k` away from an origin, which is `6*k` if `k > 0` and `1` if `k == 0`.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error maxGridRingSize(int k, int64_t* out);
```

Returns 0 (`E_SUCCESS`) if no pentagonal distortion was encountered.

</TabItem>
<TabItem value="java">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="javascript">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="python">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="go">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="duckdb">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="shell">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
</Tabs>

## gridDisk

Produces the "filled-in disk" of cells which are _at most_ grid distance `k`
from the origin cell.

Output order is not guaranteed.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error gridDisk(H3Index origin, int k, H3Index* out);
```

Elements of the output array may be left as zero,
which can happen when crossing a pentagon.

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
List<Long> gridDisk(long origin, int k);
List<String> gridDisk(String origin, int k);
```

</TabItem>
<TabItem value="javascript">

```js
h3.gridDisk(origin, k);
```

```js live
function example() {
  const h = "85283473fffffff";
  const k = 5;
  return h3.gridDisk(h, k);
}
```

</TabItem>
<TabItem value="python">

```py
h3.grid_disk(origin, k)
```

</TabItem>
<TabItem value="go">

```go
cell.GridDisk(k)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_grid_disk(origin, k)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 gridDisk --help
h3: Returns an array of a H3 cells within 'k' steps of the origin cell
H3 4.1.0

	gridDisk	Returns an array of a H3 cells within 'k' steps of the origin cell
	-h, --help	Show this help message.
	-c, --cell <index>	Required. H3 Cell
	-k <distance>	Required. Maximum grid distance for the output set
	-f, --format <FMT>	'json' for ["CELL", ...], 'newline' for CELL\n... (Default: json)
```

```bash
$ h3 gridDisk -k 5 -c 85283473fffffff
[ "85283473fffffff", "85283447fffffff", "8528347bfffffff", "85283463fffffff", "85283477fffffff", "8528340ffffffff", "8528340bfffffff", "85283457fffffff", "85283443fffffff", "8528344ffffffff", "852836b7fffffff", "8528346bfffffff", "8528346ffffffff", "85283467fffffff", "8528342bfffffff", "8528343bfffffff", "85283407fffffff", "85283403fffffff", "8528341bfffffff", "852834cffffffff", "85283453fffffff", "8528345bfffffff", "8528344bfffffff", "852836b3fffffff", "852836a3fffffff", "852836a7fffffff", "852830d3fffffff", "852830d7fffffff", "8528309bfffffff", "85283093fffffff", "8528342ffffffff", "85283423fffffff", "85283433fffffff", "852834abfffffff", "85283417fffffff", "85283413fffffff", "852834c7fffffff", "852834c3fffffff", "852834cbfffffff", "8529a927fffffff", "8529a92ffffffff", "85283697fffffff", "85283687fffffff", "852836bbfffffff", "852836abfffffff", "852836affffffff", "852830dbfffffff", "852830c3fffffff", "852830c7fffffff", "8528308bfffffff", "85283083fffffff", "85283097fffffff", "8528355bfffffff", "85283427fffffff", "85283437fffffff", "852834affffffff", "852834a3fffffff", "852834bbfffffff", "8528348ffffffff", "8528348bfffffff", "852834d7fffffff", "852834d3fffffff", "852834dbfffffff", "8529a937fffffff", "8529a923fffffff", "8529a92bfffffff", "85283693fffffff", "85283683fffffff", "8528368ffffffff", "85283617fffffff", "85283607fffffff", "85283633fffffff", "85283637fffffff", "852830cbfffffff", "852830cffffffff", "8528301bfffffff", "85283013fffffff", "8528308ffffffff", "85283087fffffff", "8528354bfffffff", "85283543fffffff", "85283553fffffff", "852835cbfffffff", "852835dbfffffff", "852834a7fffffff", "852834b7fffffff", "852834b3fffffff", "85283487fffffff", "85283483fffffff", "8528349bfffffff", "85291a6ffffffff" ]
```

</TabItem>
</Tabs>

## maxGridDiskSize

Maximum number of cells that can result from the `gridDisk` function for a given `k`.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error maxGridDiskSize(int k, int64_t *out);
```

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="javascript">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="python">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="go">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="duckdb">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="shell">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
</Tabs>

## gridDiskDistances

Produces the same set of cells as `gridDisk`, but along with each cell's
grid distance from the origin cell.

Output order is not guaranteed.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error gridDiskDistances(H3Index origin, int k, H3Index* out, int* distances);
```

Elements of the output array may be left as zero,
which can happen when crossing a pentagon.

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
List<List<Long>> gridDiskDistances(long origin, int k);
List<List<String>> gridDiskDistances(String origin, int k);
```

</TabItem>
<TabItem value="javascript">

```js
h3.gridDiskDistances(origin, k);
```

```js live
function example() {
  const h = "85283473fffffff";
  const k = 5;
  return h3.gridDiskDistances(h, k);
}
```

</TabItem>
<TabItem value="python">

:::note

This function is not exposed in Python.

:::

</TabItem>
<TabItem value="go">

```go
cell.GridDiskDistances(k)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_grid_disk_distances(origin, k)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 gridDiskDistances --help
h3: Returns an array of arrays of H3 cells, each array containing cells 'k' steps away from the origin cell, based on the outer array index
H3 4.1.0

	gridDiskDistances	Returns an array of arrays of H3 cells, each array containing cells 'k' steps away from the origin cell, based on the outer array index
	-h, --help	Show this help message.
	-c, --cell <index>	Required. H3 Cell
	-k <distance>	Required. Maximum grid distance for the output set
	-f, --format <FMT>	'json' for [["CELL", ...], ...], 'newline' for CELL\n with an extra newline between rings (Default: json)
```

```bash
$ h3 gridDiskDistances -k 5 -c 85283473fffffff
[["85283473fffffff"], ["85283447fffffff", "8528347bfffffff", "85283463fffffff", "85283477fffffff", "8528340ffffffff", "8528340bfffffff"], ["85283457fffffff", "85283443fffffff", "8528344ffffffff", "852836b7fffffff", "8528346bfffffff", "8528346ffffffff", "85283467fffffff", "8528342bfffffff", "8528343bfffffff", "85283407fffffff", "85283403fffffff", "8528341bfffffff"], ["852834cffffffff", "85283453fffffff", "8528345bfffffff", "8528344bfffffff", "852836b3fffffff", "852836a3fffffff", "852836a7fffffff", "852830d3fffffff", "852830d7fffffff", "8528309bfffffff", "85283093fffffff", "8528342ffffffff", "85283423fffffff", "85283433fffffff", "852834abfffffff", "85283417fffffff", "85283413fffffff", "852834c7fffffff"], ["852834c3fffffff", "852834cbfffffff", "8529a927fffffff", "8529a92ffffffff", "85283697fffffff", "85283687fffffff", "852836bbfffffff", "852836abfffffff", "852836affffffff", "852830dbfffffff", "852830c3fffffff", "852830c7fffffff", "8528308bfffffff", "85283083fffffff", "85283097fffffff", "8528355bfffffff", "85283427fffffff", "85283437fffffff", "852834affffffff", "852834a3fffffff", "852834bbfffffff", "8528348ffffffff", "8528348bfffffff", "852834d7fffffff"], ["852834d3fffffff", "852834dbfffffff", "8529a937fffffff", "8529a923fffffff", "8529a92bfffffff", "85283693fffffff", "85283683fffffff", "8528368ffffffff", "85283617fffffff", "85283607fffffff", "85283633fffffff", "85283637fffffff", "852830cbfffffff", "852830cffffffff", "8528301bfffffff", "85283013fffffff", "8528308ffffffff", "85283087fffffff", "8528354bfffffff", "85283543fffffff", "85283553fffffff", "852835cbfffffff", "852835dbfffffff", "852834a7fffffff", "852834b7fffffff", "852834b3fffffff", "85283487fffffff", "85283483fffffff", "8528349bfffffff", "85291a6ffffffff"]]
```

</TabItem>
</Tabs>

## gridDiskUnsafe

Produces cells within grid distance `k` of the origin cell, just like `gridDisk`.
However, the function may return an error code if pentagonal distorition is
encountered. In this case, the output in the `out` array is undefined.

Users can fall back to calling the slower but more robust `gridDiskDistances`.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error gridDiskUnsafe(H3Index origin, int k, H3Index* out);
```

Output is placed in the provided array in order of increasing distance from
the origin.
The provided array must be of size `maxGridDiskSize(k)`.

Returns 0 (`E_SUCCESS`) if no pentagonal distortion is encountered.

</TabItem>
<TabItem value="java">

```java
List<List<Long>> gridDiskUnsafe(Long h3, int k) throws PentagonEncounteredException;
List<List<String>> gridDiskUnsafe(String h3Address, int k) throws PentagonEncounteredException;
```

</TabItem>
<TabItem value="javascript">

:::note

This function is not exposed.

:::

</TabItem>
<TabItem value="python">

:::note

This function is not exposed.

:::

</TabItem>
<TabItem value="go">

:::note

This function is not exposed.

:::

</TabItem>
<TabItem value="duckdb">

```sql
h3_grid_disk_unsafe(origin, k)
```

</TabItem>
<TabItem value="shell">

:::note

This function is not exposed.

:::

</TabItem>
</Tabs>

## gridDiskDistancesUnsafe

`gridDiskDistancesUnsafe` produces indexes within `k` distance of the origin index.
Output behavior is undefined when one of the indexes returned by this
function is a pentagon or is in the pentagon distortion area.

Output is placed in the provided array in order of increasing distance from
the origin. The distances in hexagons is placed in the distances array at
the same offset. The provided array must be of size `maxGridDiskSize(k)`.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error gridDiskDistancesUnsafe(H3Index origin, int k, H3Index* out, int* distances);
```

Returns 0 (`E_SUCCESS`) if no pentagonal distortion is encountered.

</TabItem>
<TabItem value="java">

:::note

This function is not exposed because the same functionality is exposed by `gridDiskUnsafe`

:::

</TabItem>
<TabItem value="javascript">

:::note

This function is not exposed.

:::

</TabItem>
<TabItem value="python">

:::note

This function is not exposed.

:::

</TabItem>
<TabItem value="go">

:::note

This function is not exposed.

:::

</TabItem>
<TabItem value="duckdb">

```sql
h3_grid_disk_distances_unsafe(origin, k)
```

</TabItem>
<TabItem value="shell">

:::note

This function is not exposed.

:::

</TabItem>
</Tabs>

## gridDiskDistancesSafe

`gridDiskDistancesSafe` produces indexes within `k` distance of the origin index.

Output is placed in the provided array in order of increasing distance from
the origin. The distances in hexagons is placed in the distances array at
the same offset. The provided array must be of size `maxGridDiskSize(k)`.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error gridDiskDistancesSafe(H3Index origin, int k, H3Index* out, int* distances);
```

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

:::note

This function is not exposed because the same functionality is exposed by `gridDiskSafe`

:::

</TabItem>
<TabItem value="javascript">

:::note

This function is not exposed.

:::

</TabItem>
<TabItem value="python">

:::note

This function is not exposed.

:::

</TabItem>
<TabItem value="go">

:::note

This function is not exposed.

:::

</TabItem>
<TabItem value="duckdb">

```sql
h3_grid_disk_distances_safe(origin, k)
```

</TabItem>
<TabItem value="shell">

:::note

This function is not exposed.

:::

</TabItem>
</Tabs>

## gridDisksUnsafe

`gridDisksUnsafe` takes an array of input cells and a max `k` and returns an
array of cells sorted first by the original cell indices and then by the
grid ring (0 to max), with no guaranteed sorting within each grid ring group.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error gridDisksUnsafe(H3Index* h3Set, int length, int k, H3Index* out);
```

Returns 0 (`E_SUCCESS`) if no pentagonal distortion was encountered.

</TabItem>
<TabItem value="java">

:::note

This function is not exposed because the same functionality is exposed by `gridDiskUnsafe`

:::

</TabItem>
<TabItem value="javascript">

:::note

This function is not exposed.

:::

</TabItem>
<TabItem value="python">

:::note

This function is not exposed.

:::

</TabItem>
<TabItem value="go">

:::note

This function is not exposed.

:::

</TabItem>
<TabItem value="duckdb">

:::note

This function is not exposed.

:::

</TabItem>
<TabItem value="shell">

:::note

This function is not exposed.

:::

</TabItem>
</Tabs>

## gridPathCells

Given two H3 cells, return a minimal-length contiguous path of cells
between them (inclusive of the endpoint cells).

This function may fail if the cells are very far apart, or if
the cells are on opposite sides of a pentagon.

Notes:

- The output of this function should not be considered stable
  across library versions. The only guarantees are
  that the path length will be `gridDistance(start, end) + 1` and that
  every cell in the path will be a neighbor of the preceding cell.

- Paths exist in the H3 grid of cells, and may not align closely with either
  Cartesian lines or great arcs.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error gridPathCells(H3Index start, H3Index end, H3Index* out);
```

Returns 0 (`E_SUCCESS`) if no pentagonal distortion was encountered.

</TabItem>
<TabItem value="java">

```java
List<Long> gridPathCells(long start, long end) throws LineUndefinedException
List<String> gridPathCells(String startAddress, String endAddress) throws LineUndefinedException
```

</TabItem>
<TabItem value="javascript">

```js
h3.gridPathCells(start, end);
```

```js live
function example() {
  const start = "85283473fffffff";
  const end = "8528342bfffffff";
  return h3.gridPathCells(start, end);
}
```

</TabItem>
<TabItem value="python">

```py
h3.grid_path_cells(start, end)
```

</TabItem>
<TabItem value="go">

```go
cell.GridPath(other)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_grid_path_cells(start, end)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 gridPathCells --help
h3: Returns an array of H3 cells from the origin cell to the destination cell (inclusive)
H3 4.1.0

	gridPathCells	Returns an array of H3 cells from the origin cell to the destination cell (inclusive)
	-h, --help	Show this help message.
	-o, --origin <cell>	Required. The origin H3 cell
	-d, --destination <cell>	Required. The destination H3 cell
	-f, --format <FMT>	'json' for ["CELL", ...], 'newline' for CELL\n... (Default: json)
```

```bash
$ h3 gridPathCells -o 85283473fffffff -d 8528342bfffffff
[ "85283473fffffff", "85283477fffffff", "8528342bfffffff" ]
```

</TabItem>
</Tabs>

## gridPathCellsSize

Number of cells in a grid path from the start cell to the end cell,
to be used for allocating memory.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error gridPathCellsSize(H3Index start, H3Index end, int64_t* size);
```

Returns 0 (`E_SUCCESS`) on success, or an error if the path cannot be computed.

</TabItem>
<TabItem value="java">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="javascript">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="python">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="go">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="duckdb">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
<TabItem value="shell">

:::note

This function exists for memory management and is not exposed.

:::

</TabItem>
</Tabs>

## cellToLocalIj

Produces local IJ coordinates for an H3 cell anchored by an origin.

`mode` is reserved for future expansion and must be set to `0`.

This function's output is not guaranteed to be compatible across different
versions of H3.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error cellToLocalIj(H3Index origin, H3Index h3, uint32_t mode, CoordIJ *out);
```

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
CoordIJ cellToLocalIj(long origin, long h3) throws PentagonEncounteredException, LocalIjUndefinedException;
CoordIJ cellToLocalIj(String originAddress, String h3Address) throws PentagonEncounteredException, LocalIjUndefinedException;
```

</TabItem>
<TabItem value="javascript">

```js
h3.cellToLocalIj(origin, h3);
```

```js live
function example() {
  const origin = "85283473fffffff";
  const h = "8528342bfffffff";
  const { i, j } = h3.cellToLocalIj(origin, h);
  return [i, j];
}
```

</TabItem>
<TabItem value="python">

```py
h3.cell_to_local_ij(origin, h)
```

</TabItem>
<TabItem value="go">

```go
h3.CellToLocalIJ(origin, h)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_cell_to_local_ij(origin, h)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 cellToLocalIj --help
h3: Returns the IJ coordinate for a cell anchored to an origin cell
H3 4.1.0

	cellToLocalIj	Returns the IJ coordinate for a cell anchored to an origin cell
	-h, --help	Show this help message.
	-c, --cell <index>	Required. H3 Cell
	-o, --origin <cell>	Required. The origin H3 cell
	-f, --format <FMT>	'json' for [I, J], 'newline' for I\nJ\n (Default: json)
```

```bash
$ h3 cellToLocalIj -o 85283473fffffff -c 8528342bfffffff
[25, 13]
```

</TabItem>
</Tabs>

## localIjToCell

Produces an H3 cell from local IJ coordinates anchored by an origin.

`mode` is reserved for future expansion and must be set to `0`.

This function's output is not guaranteed to be compatible across different
versions of H3.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error localIjToCell(H3Index origin, const CoordIJ *ij, uint32_t mode, H3Index *out);
```

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
long localIjToCell(long origin, CoordIJ ij) throws LocalIjUndefinedException;
String localIjToCell(String originAddress, CoordIJ ij) throws LocalIjUndefinedException;
```

</TabItem>
<TabItem value="javascript">

```js
h3.localIjToCell(origin, coords);
```

```js live
function example() {
  const h = "85283473fffffff";
  const coords = { i: 0, j: 0 };
  return h3.localIjToCell(h, coords);
}
```

</TabItem>
<TabItem value="python">

```py
h3.local_ij_to_cell(origin, i, j)
```

</TabItem>
<TabItem value="go">

```go
h3.LocalIJToCell(origin, CoordIJ{i, j})
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_local_ij_to_cell(origin, i, j)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 localIjToCell --help
h3: Returns the H3 index from a local IJ coordinate anchored to an origin cell
H3 4.1.0

	localIjToCell	Returns the H3 index from a local IJ coordinate anchored to an origin cell
	-h, --help	Show this help message.
	-o, --origin <cell>	Required. The origin H3 cell
	-i <i>	Required. The I dimension of the IJ coordinate
	-j <j>	Required. The J dimension of the IJ coordinate
	-f, --format <FMT>	'json' for "CELL"\n, 'newline' for CELL\n (Default: json)
```

```bash
$ h3 localIjToCell -o 85283473fffffff -i 0 -j 0
"85280003fffffff"
```

</TabItem>
</Tabs>

# === api/vertex ===

---

id: vertex
title: Vertex functions
sidebar_label: Vertexes
slug: /api/vertex

---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

Vertex mode allows encoding the topological vertexes of H3 cells.

## cellToVertex

Returns the index for the specified cell vertex.
Valid vertex numbers are between 0 and 5 (inclusive)
for hexagonal cells, and 0 and 4 (inclusive) for pentagonal cells.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error cellToVertex(H3Index origin, int vertexNum, H3Index *out);
```

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
Long cellToVertex(long origin, int vertexNum);
String cellToVertex(String origin, int vertexNum);
```

</TabItem>
<TabItem value="javascript">

```js
h3.cellToVertex(origin, vertexNum);
```

```js live
function example() {
  const h = "85283473fffffff";
  const vertexNum = 2;
  return h3.cellToVertex(h, vertexNum);
}
```

</TabItem>
<TabItem value="python">

```py
h3.cell_to_vertex(origin, vertex_num)
```

</TabItem>
<TabItem value="go">

```go
h3.CellToVertex(origin, vertexNum)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_cell_to_vertex(origin, vertex_num)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 cellToVertex --help
h3: Returns the vertex for the specified cell and vertex index. Must be 0-5 for hexagons, 0-4 for pentagons
H3 4.1.0

	cellToVertex	Returns the vertex for the specified cell and vertex index. Must be 0-5 for hexagons, 0-4 for pentagons
	-c, --cell <index>	Required. H3 Cell
	-v, --vertex <INDEX>	Required. Vertex index number. 0-5 for hexagons, 0-4 for pentagons
	-h, --help	Show this help message.
	-f, --format <FMT>	'json' for "CELL"\n, 'newline' for CELL\n (Default: json)
```

```bash
$ h3 cellToVertex -v 2 -c 85283473fffffff
"205283463fffffff"
```

</TabItem>
</Tabs>

## cellToVertexes

Returns the indexes for all vertexes of the given cell.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Go', value: 'go'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error cellToVertexes(H3Index origin, H3Index *out);
```

The length of the `out` array must be 6.
If the given cell is a pentagon, one member of the
array will be set to `0`.

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
List<Long> cellToVertexes(long origin);
List<String> cellToVertexes(String origin);
```

</TabItem>
<TabItem value="javascript">

```js
h3.cellToVertexes(origin);
```

```js live
function example() {
  const h = "85283473fffffff";
  return h3.cellToVertexes(h);
}
```

</TabItem>
<TabItem value="python">

```py
h3.cell_to_vertexes(origin)
```

</TabItem>
<TabItem value="go">

```go
h3.CellToVertexes(origin)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_cell_to_vertexes(origin)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 cellToVertexes --help
h3: Returns all of the vertexes from the specified cell
H3 4.1.0

	cellToVertexes	Returns all of the vertexes from the specified cell
	-c, --cell <index>	Required. H3 Cell
	-h, --help	Show this help message.
	-f, --format <FMT>	'json' for ["CELL", ...], 'newline' for CELL\n... (Default: json)
```

```bash
$ h3 cellToVertexes -c 85283473fffffff
[ "22528340bfffffff", "235283447fffffff", "205283463fffffff", "255283463fffffff", "22528340ffffffff", "23528340bfffffff" ]
```

</TabItem>
</Tabs>

## vertexToLatLng

Returns the latitude and longitude coordinates of the given vertex.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
H3Error vertexToLatLng(H3Index vertex, LatLng *point);
```

Returns 0 (`E_SUCCESS`) on success.

</TabItem>
<TabItem value="java">

```java
LatLng vertexToLatLng(long vertex);
LatLng vertexToLatLng(String vertex);
```

</TabItem>
<TabItem value="javascript">

```js
h3.vertexToLatLng(vertex);
```

```js live
function example() {
  const h = "255283463fffffff";
  return h3.vertexToLatLng(h);
}
```

</TabItem>
<TabItem value="python">

```py
h3.vertex_to_latlng(vertex)
```

</TabItem>
<TabItem value="go">

```go
h3.VertexToLatLng(vertex)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_vertex_to_latlng(vertex)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 vertexToLatLng --help
h3: Returns the lat, lng pair for the given vertex
H3 4.1.0

	vertexToLatLng	Returns the lat, lng pair for the given vertex
	-c, --cell <index>	Required. H3 Cell
	-h, --help	Show this help message.
	-f, --format <FMT>	'json' for [lat, lng], 'wkt' for a WKT POINT, 'newline' for lat\nlng\n (Default: json)
```

```bash
$ h3 vertexToLatLng -c 255283463fffffff
[37.4201286777, -122.0377349643]
```

</TabItem>
</Tabs>

## isValidVertex

Determines if the given H3 index represents a valid H3 vertex.

<Tabs
groupId="language"
defaultValue="c"
values={[
{label: 'C', value: 'c'},
{label: 'Java', value: 'java'},
{label: 'JavaScript (Live)', value: 'javascript'},
{label: 'Python', value: 'python'},
{label: 'Go', value: 'go'},
{label: 'DuckDB', value: 'duckdb'},
{label: 'Shell', value: 'shell'},
]
}>
<TabItem value="c">

```c
int isValidVertex(H3Index vertex);
```

Returns 1 if the given index represents a valid H3 vertex.

</TabItem>
<TabItem value="java">

```java
boolean isValidVertex(long vertex);
boolean isValidVertex(String vertex);
```

</TabItem>
<TabItem value="javascript">

```js
h3.isValidVertex(vertex);
```

```js live
function example() {
  const h = "255283463fffffff";
  return h3.isValidVertex(h);
}
```

</TabItem>
<TabItem value="python">

```py
h3.is_valid_vertex(vertex)
```

</TabItem>
<TabItem value="go">

```go
h3.IsValidVertex(vertex)
```

</TabItem>
<TabItem value="duckdb">

```sql
h3_is_valid_vertex(vertex)
```

</TabItem>
<TabItem value="shell">

```sh
$ h3 isValidVertex --help
h3: Checks if the provided H3 vertex is actually valid
H3 4.1.0

	isValidVertex	Checks if the provided H3 vertex is actually valid
	-h, --help	Show this help message.
	-c, --cell <index>	Required. H3 Cell
	-f, --format <FMT>	'json' for true or false, 'numeric' for 1 or 0 (Default: json)
```

```bash
$ h3 isValidVertex -c 255283463fffffff
true
```

</TabItem>
</Tabs>

# === community/applications ===

---

id: applications
title: Applications Using H3
sidebar_label: Applications Using H3
slug: /community/applications

---

The following applications use H3. Contributions to this list are welcome, please feel free to open a [pull request](https://github.com/uber/h3/tree/master/website/docs/community/applications.md).

## Visualization

- [kepler.gl](http://kepler.gl/) - An open source geospatial analysis tool
- [pydeck](https://deckgl.readthedocs.io/) - High-scale spatial rendering in Python, powered by deck.gl
- [h3-viewer](https://h3.chotard.com/) - Debugging tool to visualise h3 on mercator projection, powered by deck.gl

# === community/bindings ===

---

id: bindings
title: Bindings
sidebar_label: Bindings
slug: /community/bindings

---

As a C library, bindings can be made to call H3 functions from different programming languages. This page lists different bindings currently available. Contributions to this list are welcome, please feel free to open a [pull request](https://github.com/uber/h3/tree/master/website/docs/community/bindings.md).

## Athena

- [daniel-cortez-stevenson/aws-athena-udfs-h3](https://github.com/daniel-cortez-stevenson/aws-athena-udfs-h3)

## Azure Data Explorer

- [Functions for Working with H3 Indexes](https://docs.microsoft.com/en-us/azure/data-explorer/kusto/query/geo-point-to-h3cell-function)

## BigQuery

- [CARTO Analytics Toolbox](https://github.com/CartoDB/analytics-toolbox-core#bigquery)

## C&#35;

- [entrepreneur-interet-general/h3.standard](https://github.com/entrepreneur-interet-general/H3.Standard)
- [richardvasquez/h3net](https://github.com/RichardVasquez/h3net) - A translation instead of a binding
- [pocketken/H3.net](https://github.com/pocketken/H3.net) - A translation instead of a binding

## ClickHouse

- [Functions for Working with H3 Indexes](https://clickhouse.tech/docs/en/sql-reference/functions/geo/h3/)

## Clojure

- [Factual/geo](https://github.com/Factual/geo)

## Dart

- [festelo/h3_flutter](https://github.com/festelo/h3_flutter)
- [codewithsam110g/h3_flutter_plus](https://github.com/codewithsam110g/h3_flutter_bindings)

## Databricks

- [H3 geospatial functions](https://docs.databricks.com/sql/language-manual/sql-ref-h3-geospatial-functions.html)

## Delphi

- [SkybuckFlying/h3_delphi](https://github.com/SkybuckFlying/h3_delphi)

## DuckDB

- [isaacbrodsky/h3-duckdb](https://github.com/isaacbrodsky/h3-duckdb)

## ECL

- [hpcc-systems/HPCC-Platform](https://github.com/hpcc-systems/HPCC-Platform/tree/master/plugins/h3)

## Erlang

- [helium/erlang-h3](https://github.com/helium/erlang-h3)

## Go

- [uber/h3-go](https://github.com/uber/h3-go)

## Java

- [uber/h3-java](https://github.com/uber/h3-java)

## JavaScript

- [uber/h3-js](https://github.com/uber/h3-js)
- [dfellis/h3-node](https://github.com/dfellis/h3-node)
- [realPrimoh/h3-reactnative](https://github.com/realPrimoh/h3-reactnative)

## Julia

- [wookay/H3.jl](https://github.com/wookay/H3.jl)

## Kinetica

- [H3 Functions](https://docs.kinetica.com/7.1/sql/query/#h3-functions)

## OCaml

- [travisbrady/ocaml-h3](https://github.com/travisbrady/ocaml-h3)

## Perl

- [mrdvt92/perl-Geo-H3](https://metacpan.org/pod/Geo::H3)

## PHP

- [neatlife/php-h3](https://github.com/neatlife/php-h3)
- [abler98/h3-php](https://github.com/abler98/h3-php)
- [Foysal50x/h3-php](https://github.com/Foysal50x/h3-php) - It uses PHP's built-in FFI extension, Can be installed with composer, avoiding the need to compile C code, manage system dependencies

## PostgreSQL

- [zachasme/h3-pg](https://github.com/zachasme/h3-pg)

## Presto

- [foursquare/h3-presto](https://github.com/foursquare/h3-presto)

## Python

- [uber/h3-py](https://github.com/uber/h3-py)
- [DahnJ/H3-Pandas](https://github.com/DahnJ/H3-Pandas)
- [filimoa/h3-polars](https://github.com/Filimoa/polars-h3)

## R

- [scottmmjackson/h3r](https://github.com/scottmmjackson/h3r)
- [crazycapivara/h3-r](https://github.com/crazycapivara/h3-r)
- [obrl-soil/h3jsr](https://github.com/obrl-soil/h3jsr)

## Ruby

- [seanhandley/h3_ruby](https://github.com/seanhandley/h3_ruby)

## Rust

- [rustyconover/libh3-sys](https://github.com/rustyconover/libh3-sys)
- [rustyconover/libh3](https://github.com/rustyconover/libh3)
- [nmandery/h3ron](https://github.com/nmandery/h3ron)
- [HydroniumLabs/h3o](https://github.com/HydroniumLabs/h3o) - A translation instead of a binding

## Snowflake

- [CARTO Analytics Toolbox](https://github.com/CartoDB/analytics-toolbox-core#snowflake)

## SQLite3

- [isaacbrodsky/h3-sqlite3](https://github.com/isaacbrodsky/h3-sqlite3)

## SQL Server

- [tbbuck/H3.net.SqlClr](https://github.com/tbbuck/H3.net.SqlClr)

## Spark

- [jchotard/h3spark](https://github.com/JosephChotard/h3spark) (4.x)
- [kevinschaich/h3-pyspark](https://github.com/kevinschaich/h3-pyspark) (3.x)

## Swift

- [JeremyEspresso/swift-h3](https://github.com/JeremyEspresso/swift-h3) (4.x)
- [pawelmajcher/SwiftyH3](https://github.com/pawelmajcher/SwiftyH3) (4.x)

# === community/libraries ===

---

id: libraries
title: Libraries Using H3
sidebar_label: Libraries Using H3
slug: /community/libraries

---

The following libraries use H3 via one of its bindings. Contributions to this list are welcome, please feel free to open a [pull request](https://github.com/uber/h3/tree/master/website/docs/community/libraries.md).

## JavaScript

- [uber/geojson2H3](https://github.com/uber/geojson2H3) - Conversion utilities between H3 indexes and GeoJSON

## Python

- [nmandery/h3ronpy](https://github.com/nmandery/h3ronpy) - Raster to H3 conversion, smoothing of linked polygons.

## Rust

- [nmandery/h3ron](https://github.com/nmandery/h3ron) - Raster to H3 conversion, smoothing of linked polygons.

# === community/tutorials ===

---

id: tutorials
title: Learning Resources
sidebar_label: Learning Resources
slug: /community/tutorials

---

This page lists further learning materials and code walkthroughs for the H3 library and bindings. Contributions to this list are welcome, please feel free to open a [pull request](https://github.com/uber/h3/tree/master/website/docs/community/tutorials.md).

## Community

- [H3 Slack workspace](https://join.slack.com/t/h3-core/shared_invite/zt-g6u5r1hf-W_~uVJmfeiWtMQuBGc1NNg)

## Videos

- [Introduction to H3](https://www.youtube.com/watch?v=wDuKeUkNLkQ) (June 2019)
- [Engineering an H3-based Geospatial Data Platform at Uber](https://www.youtube.com/watch?v=aCj-YVZ0mlE)
- [Building City Cores with H3](https://www.youtube.com/watch?v=PutOhe8HVNU)
- [H3-js: Hexagons in the Browser](https://www.youtube.com/watch?v=BsMIrBHLfLE&list=PLLEUtp5eGr7CNf9Bj3w3i30rzaU8lKZeV&index=16&t=0s)
- [Hexagon Convolution for Data Smoothing & Forecasting](https://www.youtube.com/watch?v=z3PaGIQTFSE&list=PLLEUtp5eGr7CNf9Bj3w3i30rzaU8lKZeV&index=14&t=0s)
- [Spatial Intelligence Using Hex](https://www.youtube.com/watch?v=0OlIpNAqokQ&list=PLLEUtp5eGr7CNf9Bj3w3i30rzaU8lKZeV&index=18&t=0s)
- [Hierarchical Hexagons in Depth](https://www.youtube.com/watch?v=UILoSqvIM2w&list=PLLEUtp5eGr7CNf9Bj3w3i30rzaU8lKZeV&index=15&t=0s)
- [H3: Tiling the Earth with Hexagons](https://www.youtube.com/watch?v=_-265mfMzl4&list=PLLEUtp5eGr7CNf9Bj3w3i30rzaU8lKZeV&index=22&t=0s) (Introduction to H3, November 2018)
- [H3: Tiling the Earth with Hexagons](https://www.youtube.com/watch?v=ay2uwtRO3QE) (Introduction to H3, January 2018)

## Java

- [H3 Measurements](https://github.com/isaacbrodsky/h3measurements): Measurements of average cell area, average cell perimeter length, truncation error, and so on.

## JavaScript

- [H3 Tutorials on Observable](https://beta.observablehq.com/collection/@nrabinowitz/h3-tutorial)

## Python

- [Usage (IPython Notebook)](https://github.com/uber/h3-py-notebooks/blob/master/notebooks/usage.ipynb)
- [Unified Data Layers (IPython Notebook)](https://github.com/uber/h3-py-notebooks/blob/master/notebooks/unified_data_layers.ipynb)
- [H3 API examples on Urban Analytics (IPython Notebook)](https://github.com/uber/h3-py-notebooks/blob/master/notebooks/urban_analytics.ipynb)

# === comparisons/admin ===

---

id: admin
title: Admin Boundaries
sidebar_label: Admin Boundaries
slug: /comparisons/admin

---

Administrative boundaries, such as ZIP Codes and Census Blocks in the United States, can be used for aggregating and analyzing data. These boundaries have a number of drawbacks for aggregating data. These are primarily related to not having a comparable spatial unit of analysis, being unable to spatially relate data, and being unrelated to the data being analyzed.

## ZIP Codes

The article [Stop Using Zip Codes for Geospatial Analysis](https://towardsdatascience.com/stop-using-zip-codes-for-geospatial-analysis-ceacb6e80c38) summarizes a number of problems with using ZIP Codes. In short, ZIP Codes do not represent areas themselves but rather mail delivery routes. They also vary greatly in spatial size when rendered as ZIP Code Tabulation Areas and [change for unrelated reasons](https://fas.org/sgp/crs/misc/RL33488.pdf).

## Use case specific partitioning

When using manually drawn partitions, there is usually no spatial unit of analysis which can be compared. Edges of partitions may exhibit boundary effects due to not taking into account neighboring partitions.

Manually drawn partitions can better incorporate human knowledge, but can require updating as that knowledge changes. It can take a significant amount of time and effort to define and update partitions manually.

The varying size of partitions means the center of a partition may be unrelated to the center of the data points.

## ZIP Codes vs H3 comparison

<iframe width="100%" height="500px" src="https://studio.unfolded.ai/public/72504bc0-184e-4ba0-b10b-72fdf61e2c33/embed" frameborder="0" allowfullscreen></iframe>

ZIP Codes on the left, H3 on the right. Data: [New York City 2015 Street Tree Census](https://data.cityofnewyork.us/Environment/2015-Street-Tree-Census-Tree-Data/uvpi-gqnh)

# === comparisons/geohash ===

---

id: geohash
title: Geohash
sidebar_label: Geohash
slug: /comparisons/geohash

---

[Geohash](https://en.wikipedia.org/wiki/Geohash) is a system for encoding locations using a string of characters, creating a hierarchical, square grid system (a quadtree).

## Area distortion

Because Geohash encodes latitude and longitudes pairs, it is subject to significant differences in area at different latitudes. A degree of longitude near a pole represents a significantly smaller distance than a degree of longitude near the equator.

## Identifiers

Geohash uses strings for its cell indexes. Because they are strings, they can encode arbitrarily precise cells.

H3 cell indexes are designed to be 64 bit integers, which can be rendered and transmitted as strings if needed. The integer representation can be used when high performance is needed, as integer operations are usually more performant than string operations. Because indexes are fixed size, H3 has a maximum resolution it can encode.

## Geohash vs H3 Comparison

<iframe width="100%" height="500px" src="https://studio.unfolded.ai/public/009a4f1e-2b74-4c0f-a156-95051c6583f3/embed" frameborder="0" allowfullscreen></iframe>

Geohash on the left, H3 on the right. Data: [San Francisco Street Tree List](https://data.sfgov.org/City-Infrastructure/Street-Tree-List/tkzw-k3nq)

# === comparisons/hexbin ===

---

id: hexbin
title: Hexbin
sidebar_label: Hexbin
slug: /comparisons/hexbin

---

Hexbinning is the process of taking coordinates and binning them into hexagonal cells in analytics or mapping software. The size of the hexagons is configurable, and the hexagons can align with the map projection being used.

Hexbins are generally very computationally cheap to create, and for the best performance can be computed directly on a GPU. Their coordinates, while not hierarchical, support many common operations like finding neighbors and grid distances very efficiently.

Hexbins have drawbacks in the ability to reuse the grids. The cell identifiers they use are only useful in the specific hexbin grid, and are not portable to another grid, limiting their ability to be used for joining datasets. The cell identifiers are not hierarchical, so relating data at different grid resolutions can be difficult.

Hexbins are also limited by the projection system they are created on top of. This usually results in discontinuities at the edges of the projections, for example at the anti-meridian or at the poles.

## Hexbin vs H3 Comparison

<iframe width="100%" height="500px" src="https://studio.unfolded.ai/public/0beb2afb-9dd4-400b-90dd-f61580c582b9/embed" frameborder="0" allowfullscreen></iframe>

Hexbins on the left, H3 on the right. Data: [San Francisco Street Tree List](https://data.sfgov.org/City-Infrastructure/Street-Tree-List/tkzw-k3nq)

# === comparisons/placekey ===

---

id: placekey
title: Placekey
sidebar_label: Placekey
slug: /comparisons/placekey

---

[Placekey](https://www.placekey.io/) is a system for encoding points of interest (POIs), and incorporates H3 in its POI identifier.

For example, the Placekey for the Ferry Building in San Francisco, `zzw-22y@5vg-7gt-qzz`, contains a What Part (`zzw-22y`) encoding a specific POI, and a Where Part (`5vg-7gt-qzz`) encoding where that POI is. The Where Part is an H3 cell index at resolution 10, using an alternate string encoding. The example Where Part represents the H3 index `8a283082a677fff`. Placekey Where Parts can be losslessly converted to and from their equivalent H3 indexes.

# === comparisons/s2 ===

---

id: s2
title: S2
sidebar_label: S2
slug: /comparisons/s2

---

[S2](https://s2geometry.io/), like H3, implements an open source, hierarchical, discrete, and global grid system. The systems share a number of similarities, including the use of 64 bit integers as cell indexes, making it very efficient to use both of them in big data systems.

One of the main differences between S2 and H3 is the choice of cell shape. S2 uses square cells while H3 uses hexagonal cells. This leads to important differences in neighbors, subdivision, and visualization.

## Neighbors

Squares have two classes of neighbors: those that they share an edge with, and those that they share a point with. This can complicate analysis of moving things in the real world, because they are very unlikely to move in a way aligned with the grid. Instead, the analyst will need to account for different types of neighbors.

Hexagons have only one class of neighbor, that they share an edge with. This makes running convolutions and smoothing over the data much simpler, since only the grid distance (as opposed to the geographic distance) from a cell needs to be considered.

## Subdivision

S2 uses an _aperture 4_ system where each cell is subdivided into 4 finer, child cells. Squares subdivide exactly into 4 child squares. This means that when indexing a point to an S2 cell, and then truncating to the parent S2 cell, there is no possibility that the point is not contained in the bounds of the parent cell.

This differs from H3 where the same operation is approximate. This is the case because hexagons do not exactly subdivide into 7 child hexagons.

## Visualization

S2 cells are squares in the system's projection. When those cells are visualized on a map using a projection like the Web Mercator projection, the cells can subjectively appear distorted (i.e. as a quadrilateral rather than square).

H3 cells have the same non-alignment with the map projection, but in our experience the effect is less noticeable to viewers for hexagons.

## Links

- [Geometry on the Sphere: Google's S2 Library](https://docs.google.com/presentation/d/1Hl4KapfAENAOf4gv-pSngKwvS_jwNVHRPZTTDzXXn6Q/edit)

## S2 vs H3 Comparison

<iframe width="100%" height="500px" src="https://studio.unfolded.ai/public/851dc25a-c8c8-4f20-96b8-ea47b3e3e9a7/embed" frameborder="0" allowfullscreen></iframe>

S2 on the left, H3 on the right. Data: [San Francisco Street Tree List](https://data.sfgov.org/City-Infrastructure/Street-Tree-List/tkzw-k3nq)

# === core-library/cellToBoundaryDesc ===

---

id: cellToBoundaryDesc
title: Generate the cell boundary in latitude/longitude coordinates of an H3Index cell
sidebar_label: Generate the cell boundary in latitude/longitude coordinates of an H3Index cell
slug: /core-library/cellToBoundaryDesc

---

This operation is performed by function `cellToBoundary`. See the comments in the function source code for more detail.

The conversion is performed as a series of coordinate system conversions described below. See the page [Coordinate Systems used by the H3 Core Library](/docs/core-library/coordsystems) for more information on each of these coordinate systems.

1. We note that the cell vertices are the center points of cells in an aperture 3 grid one resolution finer than the cell resolution, which we term a _substrate_ grid. We precalculate the substrate _ijk_ coordinates of a cell with _ijk_ coordinates (0,0,0), adding additional aperture 3 and aperture 7 (if required, by Class III cell grid) substrate grid resolutions as required to transform the vertex coordinates into a Class II substrate grid.

<div align="center">
  <img height="300" src="/images/substrate3.png" />
</div>

2. The function `_faceIjkToGeoBoundary` calculates the _ijk_ coordinates of the cell center point in the appropriate substrate grid (determined in the last step), and each of the substrate vertices is translated using the cell center point _ijk_. Each vertex _ijk_ is then transformed onto the appropriate face and _Hex2d_ coordinate system using the approach taken in [finding a cell center point](/docs/core-library/cellToLatLngDesc). If adjacent vertices lie on different icosahedron faces a point is introduced at the intersection of the cell edge and icosahedron face edge.
3. The _Hex2d_ coordinates are then converted to latitude/longitude using `_hex2dToGeo`.

# === core-library/cellToLatLngDesc ===

---

id: cellToLatLngDesc
title: Determine the latitude/longitude coordinates of the center point of an H3Index cell
sidebar_label: Determine the latitude/longitude coordinates of the center point of an H3Index cell
slug: /core-library/cellToLatLngDesc

---

This operation is performed by function `cellToLatLng`. See the comments in the function source code for more detail.

The conversion is performed as a series of coordinate system conversions described below. See the page [Coordinate Systems used by the H3 Core Library](/docs/core-library/coordsystems) for more information on each of these coordinate systems.

1.  The function `_h3ToFaceIjk` then converts the H3 index to the appropriate icosahedron face number and normalized _ijk_ coordinate's on that face's coordinate system as follows:

- We start by assuming that the cell center point falls on the same icosahedron face as its base cell.
- It is possible that the cell center point lies on an adjacent face (termed an _overage_ in the code), in which case we would need to use a projection centered on that adjacent face instead. We recall that normalized _ijk_ coordinates have at most two non-zero components, and that in a face-centered Class II system the sum of those components is a resolution-specific constant value for cells that lie on the edge of that icosahedral face.
  We determine whether an overage exists by taking the sum of the _ijk_ components, and if there is an overage the positive _ijk_ components indicate which adjacent face the cell center lies on. A lookup operation is then performed to find the appropriate rotation and translation to transform the _ijk_ coordinates into the adjacent face-centered _ijk_ system.

<div align="center">
  <img height="300" src="/images/triEdge.png" />
</div>

2. The face-centered _ijk_ coordinates are then converted into corresponding _Hex2d_ coordinates using the function `_ijkToHex2d`.
3. The function `_hex2dToGeo` takes the _Hex2d_ coordinates and scales them into face-centered gnomonic coordinates, and then performs an inverse gnomonic projection to get the latitude/longitude coordinates.

# === core-library/compilation-options ===

---

id: compilation-options
title: Compilation options
sidebar_label: Compilation options
slug: /core-library/compilation-options

---

A number of options in CMake can be set when compiling the H3 core library. These are relevant for building
different ways of using and testing the library and do not affect the underlying algorithms.

When configuring with CMake, an option may be specified using `-D` on the command line, like so for setting
`CMAKE_BUILD_TYPE` to `Release`:

```bash
cmake .. -DCMAKE_BUILD_TYPE=Release
```

Boolean options should be set to `ON` or `OFF`, like so:

```bash
cmake .. -DBUILD_TESTING=OFF
```

## AUDIT_SOURCE_FILE_LIST

Whether to glob the list of source files and compare it to the `ALL_SOURCE_FILES` and `EXAMPLE_SOURCE_FILES` lists
defined in CMake. This is a quality control measure to ensure that the source file list in `CMakeLists.txt` actually
matches the sources in the repository and is not missing any files.

## BUILD_ALLOC_TESTS

Whether to build the parts of the [test suite](./testing) that exercise the [H3_ALLOC_PREFIX](./custom-alloc) feature.

## BUILD_BENCHMARKS

Whether to build the [benchmark suite](./testing#benchmarks).

## BUILD_COUNTRY_BENCHMARKS

Whether to build benchmarks that use [Natural Earth](https://github.com/nvkelso/natural-earth-vector/) geometries.

The geometries will be downloaded at build time using Node.

## BUILD_FILTERS

Whether to build the [H3 command line filter](./filters) executables.

## BUILD_GENERATORS

Whether to build generator executables used in the development of H3. This is not required for
building the library as the output of these generators is checked in.

## BUILD_TESTING

Whether to build the [test suite](./testing).

## BUILD_FUZZERS

Whether to build the [fuzzer suite](./testing#fuzzers).

## ENABLE_LIBFUZZER

Whether to build the fuzzers with [libFuzzer](https://www.llvm.org/docs/LibFuzzer.html) (this expects to be used with Clang). If OFF, a `main` function suitable for use with [American fuzzy lop](https://lcamtuf.coredump.cx/afl/) is included.

## CMAKE_BUILD_TYPE

Should be set to `Release` for production builds, and `Debug` in development.

## ENABLE_COVERAGE

Whether to compile `Debug` builds with coverage instrumentation (compatible with GCC, Clang, and lcov). This also excludes defensive code in the library that should not be counted against coverage because it is unreachable.

## ENABLE_DOCS

Whether to build the Doxygen documentation. This is not the same as the [H3 website](https://github.com/uber/h3/tree/master/website),
but is rather the documentation for the internal C library functions.

## ENABLE_FORMAT

Whether to enable using clang-format-14 to format source files before building. This should be enabled
before submitting patches for H3 as continuous integration will fail if the formatting does not match.

Only this version of clang-format should be used to format the sources as new releases of clang-format
can change defaults, causing unintended churn of source code formatting.

## ENABLE_LINTING

Whether to enable using clang-tidy to lint source files when building. Only invoked when
[Makefile or Ninja CMake generators](https://cmake.org/cmake/help/latest/prop_tgt/LANG_CLANG_TIDY.html)
are used.

## H3_ALLOC_PREFIX

Used for directing the library to use a [different set of functions for memory management](./custom-alloc).

## H3_PREFIX

Used for [renaming the public API](./usage#function-renaming).

## PRINT_TEST_FILES

If enabled, CMake will print which CTest test case corresponds to which input file.

## ENABLE_WARNINGS

Whether to enable all compiler warnings. (i.e. [`-Wall`](https://gcc.gnu.org/onlinedocs/gcc/Warning-Options.html#index-Wall))

## WARNINGS_AS_ERRORS

Whether to treat compiler warnings as errors. While a useful tool for ensuring software quality, this should not be enabled
for production builds as compiler warnings can change unexpectedly between versions. This is intended to be used with
`ENABLE_WARNINGS` on.

## WRAP_VALGRIND

Whether to wrap invocations of the test suite with `valgrind` (if available).

# === core-library/coordsystems ===

---

id: coordsystems
title: Coordinate systems
sidebar_label: Coordinate systems
slug: /core-library/coordsystems

---

The H3 Core Library uses the following coordinate systems internally.

## IJK Coordinates

Discrete hexagon planar grid systems naturally have 3 coordinate axes spaced 120&deg; apart. We refer to such a system as an _ijk coordinate system_, for the three coordinate axes _i_, _j_, and _k_. A single _ijk_ coordinate triplet is represented in the H3 Core Library using the structure type `CoordIJK`.

Using an _ijk_ coordinate system to address hexagon grid cells provides multiple valid addresses for each cell. _Normalizing_ an _ijk_ address (function `_ijkNormalize`) creates a unique address consisting of the minimal positive _ijk_ components; this always results in at most two non-zero components.

<div align="center">
  <img height="300" src="/images/ijkp.png" />
</div>

## FaceIJK Coordinates

The H3 Core Library centers an _ijk_ coordinate system on each face of the icosahedron; the combination of a face number and _ijk_ coordinates on that face's coordinate system is represented using the structure type `FaceIJK`.

Each grid resolution is rotated ~19.1&deg; relative to the next coarser resolution. The rotation alternates between counterclockwise and clockwise at each successive resolution, so that each resolution will have one of two possible orientations: _Class II_ or _Class III_ (using a terminology coined by R. Buckminster Fuller). The base cells, which make up resolution 0, are _Class II_.

<div align="center">
  <img height="300" src="/images/classII.III.png" />
</div>

## Hex2d Coordinates

A _Hex2d_ coordinate system is a cartesian coordinate system associated with a specific _ijk_ coordinate system, where:

- the origin of the _Hex2d_ system is centered on the origin cell of the _ijk_ system,
- the positive _x_-axis of the _Hex2d_ system is aligned with the _i_-axis of the _ijk_ system, and
- 1.0 unit distance in the _Hex2d_ system is the distance between adjacent cell centers in the _ijk_ coordinate system.

_Hex2d_ coordinates are represented using the structure type `Vec2d`.

## Local IJ Coordinates

Algorithms working with hexagons may want to refer to grid coordinates that are not interrupted by base cells or faces. These coordinates have 2 coordinate axes spaced 120&deg; apart, with the coordinates anchored by an _origin_ H3 index.

- local coordinates are only comparable when they have the same _origin_ index.
- local coordinates are only valid near the _origin_. Pratically, this is within the same base cell or a neighboring base cell, except for pentagons.
- the coordinate space may have deleted or warped regions due to pentagon distortion.
- there may be multiple coordinates for the same index, with the same _origin_.
- the _origin_ may not be at `(0, 0)` in the local coordinate space.

_Local IJ_ coordinates are represented using the structure type `CoordIJ` and an associated _origin_ `H3Index`.

# === core-library/creating-bindings ===

---

id: creating-bindings
title: Creating bindings for H3
sidebar_label: Creating bindings
slug: /core-library/creating-bindings

---

H3 is a C library, in part to make it simpler to create bindings for different programming languages. Each language usually has its own way to bind to C functions, but this document can serve as a starting point and list of tips.

There may already be [H3 bindings](/docs/community/bindings) available for your language of choice.

## Function naming

The `make binding-functions` target produces a file `binding-functions` containing a list of function in the H3 public API, one per line. You can use this as part of your build process to check how much of the H3 public API your bindings expose. This list does not include memory management functions that are needed to allocate arrays to be passed to the H3 API.

Keeping similar names and purposes for functions can make it easier for your users to use the H3 [API Reference](/docs/api/indexing).

## Community

When ready, make a [pull request](https://github.com/uber/h3/edit/master/docs/community/bindings.md) to add your binding to the H3 documentation website.

## Documentation

To be included in the H3 [API reference](/docs/api/indexing), your binding should:

- Be reasonably up to date with uber/h3.
- Include bindings for the relevant functions in the output of `make binding-functions`. For example, `stringToH3` may not be necessary if your bindings only supports string H3 indexes.
- Use the major and minor version of the version of H3 bound. For example, when binding H3 version 3.2.1, a valid binding version would be 3.2.0, but 4.2.1 would not be valid.

# === core-library/custom-alloc ===

---

id: custom-alloc
title: Memory allocation
sidebar_label: Memory allocation
slug: /core-library/custom-alloc

---

H3's approach to memory management is to rely on memory allocated by the caller as much as possible. This allows memory to be managed by an external framework.

In some cases (for example, `polygonToCells`), H3 allocates heap memory. When this is needed, it uses the standard C memory allocation functions.

## Custom Memory Allocators

:::caution

On some systems, such as Windows, the undefined symbols cannot be undefined at build time. Further changes to the H3 build are needed to provide custom implementations.

:::

:::caution

There are a few algorithms like `kRing` that still use the call stack to recurse and could run out of memory that way.

:::

H3 supports replacing the memory management functions (`malloc`, `calloc`, `realloc`, `free`) used by the library at build time. This can be used to integrate H3 within a managed framework.

When using custom memory allocators, H3 prefixes the names of memory allocation functions with the string you specify. The application linking H3 must have the prefixed replacement functions defined, or you must change the H3 build to link against the prefixed replacement functions.

When building H3, specify the `H3_ALLOC_PREFIX` option to your prefix of choice, as below:

```bash
cmake -DH3_ALLOC_PREFIX=my_prefix_ .
```

Then, in your application using H3, implement the following functions, replacing `my_prefix_` with the prefix you chose above:

```c
void* my_prefix_malloc(size_t size);
void* my_prefix_calloc(size_t num, size_t size);
void* my_prefix_realloc(void* ptr, size_t size);
void my_prefix_free(void* ptr);
```

:::info

H3 does not currently use `realloc`.

:::

Link to H3 as you would have without the custom allocators. The custom allocators will be used for allocating heap memory in H3.

# === core-library/filters ===

---

id: filters
title: Unix-style Filters for H3
sidebar_label: Unix-style Filters for H3
slug: /core-library/filters

---

The directory `src/apps/filters` contains unix-style stdin/stdout filters that perform conversions between integer H3 indexes and other useful types. It currently contains the filters listed in the table below. See the header comments in each application source code file for more information.

Filters are experimental and are not part of the semantic version of the H3 library.

All latitude/longitude coordinates are in decimal degrees. See the [H3 Index Representations](/docs/core-library/h3indexing) page for information on the integer `H3Index`.

| filter           | input     | outputs                         |
| ---------------- | --------- | ------------------------------- |
| `latLngToCell`   | lat/lng   | `H3Index`                       |
| `cellToLatLng`   | `H3Index` | cell center point in lat/lng    |
| `cellToBoundary` | `H3Index` | cell boundary in lat/lng        |
| `h3ToComponents` | `H3Index` | components                      |
| `gridDisk`       | `H3Index` | surrounding `H3Index`           |
| `gridDiskUnsafe` | `H3Index` | surrounding `H3Index`, in order |

## Unix Command Line Examples

- find the index for coordinates at resolution 5

  `latLngToCell --resolution 5 --latitude 40.689167 --longitude -74.044444`

- output the cell center point for `H3Index` 845ad1bffffffff

  `cellToLatLng --index 845ad1bffffffff`

- output the cell boundary for `H3Index` 845ad1bffffffff

  `cellToBoundary --index 845ad1bffffffff`

- find the components for the `H3Index` 845ad1bffffffff

  `h3ToComponents --index 845ad1bffffffff`

- output all indexes within distance 1 of the `H3Index` 845ad1bffffffff

  `kRing -k 1 --origin 845ad1bffffffff`

- output all hexagon indexes within distance 2 of the `H3Index` 845ad1bffffffff

  `hexRange -k 2 --origin 845ad1bffffffff`

Note that the filters `cellToLatLng` and `cellToBoundary` take optional arguments that allow them to generate `kml` output. See the header comments in the corresponding source code files for details.

# === core-library/latLngToCellDesc ===

---

id: latLngToCellDesc
title: Conversion from latitude/longitude to containing H3 cell index
sidebar_label: Conversion from latitude/longitude to containing H3 cell index
slug: /core-library/latLngToCellDesc

---

This operation is performed by function `latLngToCell`. See the comments in the function for more detail.

The conversion is performed as a series of coordinate system conversions described below. See the page [Coordinate Systems used by the H3 Core Library](/docs/core-library/coordsystems) for more information on each of these coordinate systems.

1. The input latitude/longitude coordinate is first converted into the containing icosahedron face and a _Hex2d_ coordinate on that face using function `_geoToHex2d`, which determines the correct face and then performs a face-centered gnomonic projection into face-centered polar coordinates. These polar coordinates are then scaled appropriately to a _Hex2d_ coordinate on the input grid resolution _r_.
2. The _Hex2d_ coordinate is converted into resolution _r_ normalized _ijk_ coordinates using function `_hex2dToCoordIJK`.
3. The face and face-centered _ijk_ coordinates are then converted into an `H3Index` representation using the following steps:
   1. The H3 index digits are calculated from resolution _r_ up to 0, adjusting the _ijk_ coordinates at each successively coarser resolution.
   2. When resolution 0 is reached, if the remaining _ijk_ coordinates are (0,0,0) then the base cell centered on the face is chosen for the index.
   3. If the remaining resolution 0 _ijk_ coordinates are not (0,0,0), then a lookup operation is performed to find the appropriate base cell and the required rotation (if any) to orient the cell in that base cell's coordinate system. The index is then translated and rotated into the coordinate system centered on the new base cell.

# === core-library/overview ===

---

id: overview
title: Overview of the H3 Geospatial Indexing System
sidebar_label: Overview
slug: /core-library/overview

---

The H3 geospatial indexing system is a discrete global grid system (see [Sahr et al., 2003](http://webpages.sou.edu/~sahrk/sqspc/pubs/gdggs03.pdf)) consisting of a multi-precision hexagonal tiling of the sphere with hierarchical indexes.

The hexagonal grid system is created on the planar faces of a sphere-circumscribed icosahedron, and the grid cells are then projected to the surface of the sphere using an inverse face-centered polyhedral gnomonic projection. The coordinate reference system (CRS) is spherical coordinates with the [WGS84](https://en.wikipedia.org/wiki/WGS84)/[EPSG:4326](https://epsg.io/4326) authalic radius. It is common to use WGS84 CRS data with the H3 library.

The icosahedron is fixed relative to the sphere using a _Dymaxion_ orientation (due to R. Buckminster Fuller). This orientation of a spherical icosahedron places all 12 icosahedron vertices in the ocean. (At the time of H3's development, this was the only known orientation with this property. [Others have since been found](https://richard.science/sci/2019_barnes_dgg_published.pdf).)

The H3 grid is constructed on the icosahedron by recursively creating increasingly higher precision hexagon grids until the desired resolution is achieved. Note that it is impossible to tile the sphere/icosahedron completely with hexagons; each resolution of an icosahedral hexagon grid must contain exactly 12 pentagons at every resolution, with one pentagon centered on each of the icosahedron vertices.

The first H3 resolution (resolution 0) consists of 122 cells (110 hexagons and 12 icosahedron vertex-centered pentagons), referred to as the _base cells_. These were chosen to capture as much of the symmetry of the spherical icosahedron as possible. These base cells are assigned numbers from 0 to 121 based on the latitude of their center points; base cell 0 has the northern most center point, while base cell 121 has the southern most center point.

Each subsequent resolution beyond resolution 0 is created using an aperture 7 resolution spacing (aperture refers to the number of cells in the next finer resolution grid for each cell); as resolution increases the unit length is scaled by `sqrt(7)` and each hexagon has 1/7<sup>th</sup> the area of a hexagon at the next coarser resolution (as measured on the icosahedron). H3 provides 15 finer grid resolutions in addition to the resolution 0 base cells. The finest resolution, resolution 15, has cells with an area of less than 1 m<sup>2</sup>. A table detailing the average cell area for each H3 resolution is available [here](/docs/core-library/restable).

_Note:_ you can create KML files to visualize the H3 grids by running the `kml` make target. It will place the files in the `KML` output sub-directory.

# === core-library/testing ===

---

id: testing
title: Testing strategy
sidebar_label: Testing strategy
slug: /core-library/testing

---

The H3 developers try to ensure the robustness and reliability of the H3 library. Tools used to do this include defensive code, unit tests with coverage reporting, and fuzzing.

The H3 library may despite these efforts behave unexpectedly; in these cases the developers
[welcome feedback and contributions](https://github.com/uber/h3/blob/master/CONTRIBUTING.md).

## Unit testing

Github Actions are used to run the H3 test suite for every commit. A variety of configurations, described below, are tested.

Coverage information is collected in Coveralls. Because of the self-contained nature of the H3 library, we seek to have as close to 100% code coverage as possible.

| Operating system | Compiler    | Build type     | Processor architecture | Special notes                                                                                         |
| ---------------- | ----------- | -------------- | ---------------------- | ----------------------------------------------------------------------------------------------------- |
| Linux (Ubuntu)   | Clang       | Debug, Release | x64                    | clang-format-14 is used to ensure all code is consistently formatted                                  |
| Linux            | Clang       | Debug          | x64                    | An additional copy of the job runs with [Valgrind](https://valgrind.org/)                             |
| Linux            | Clang       | Debug          | x64                    | An additional copy of the job runs with coverage reporting, and excerising the `H3_PREFIX` mechanism. |
| Linux            | gcc         | Debug, Release | x64                    |
| Mac OS           | Apple Clang | Debug, Release | x64                    |
| Windows          | MSVC        | Debug, Release | x64                    | Static library                                                                                        |
| Windows          | MSVC        | Debug, Release | x86                    | Static library                                                                                        |
| Windows          | MSVC        | Debug, Release | x64                    | Dynamic library; testing is not run in this configuration                                             |
| Windows          | MSVC        | Debug, Release | x86                    | Dynamic library; testing is not run in this configuration                                             |

## Defensive code

H3 uses preprocessor macros borrowed from [SQLite's testing methodology](https://www.sqlite.org/testing.html) to include defensive code in the library. Defensive code is code that handles error conditions for which there are no known test cases to demonstrate it. The lack of known test cases means that without the macros, the defensive cases could inappropriately reduce coverage metrics, disincentivizing including them. The macros behave differently, depending on the build configuration:

- Under release builds of the library (`CMAKE_BUILD_TYPE=Release`), the defensive code is included without modification. These branches are intended to be very simple (usually only `return`ing an error code and possibly `free`ing some resources) and to be visually inspectable.

- Under debug builds of the library (`CMAKE_BUILD_TYPE=Debug`), the defensive code is included and `assert` calls are included if the defensive code is invoked. Any unit test or fuzzer which can demonstrate the defensive code is actually reached will trigger a test failure and the developers can be alerted to cover the defensive code in unit tests.

- Under coverage builds of the library (`CMAKE_BUILD_TYPE=Debug ENABLE_COVERAGE=ON`), the defensive code is not included by replacing its condition with a constant value. The compiler removes the defensive code and it is not counted in coverage metrics. This is intended only for determining test coverage of the library.

## Benchmarks

H3 uses benchmarks to offer a comparison of the library's performance between revisions.

Benchmarks are automatically run on Linux x64 with Clang and GCC compilers for each commit in Github Actions.

## Fuzzers

H3 uses [fuzzers](https://github.com/uber/h3/tree/master/src/apps/fuzzers) to find novel inputs that crash or result in other undefined behavior.

On each commit, CI is triggered to run [OSS-Fuzz](https://github.com/google/oss-fuzz/tree/master/projects/h3) for H3. OSS-Fuzz regularly runs fuzzers against the latest development version of H3 and reports newly discovered issues to the H3 core maintainers.

# === core-library/usage ===

---

id: usage
title: Public API
sidebar_label: Public API
slug: /core-library/usage

---

The public API of the H3 Core Library is defined in the file [`h3api.h`](https://github.com/uber/h3/blob/master/src/h3lib/include/h3api.h.in).

## API Versioning

The functions defined in `h3api.h` adhere to [Semantic Versioning](https://semver.org/).

## Header preprocessing

The file `h3api.h.in` is preprocessed into the file `h3api.h` as part of H3's build process. The preprocessing inserts the correct values for the `H3_VERSION_MAJOR`, `H3_VERSION_MINOR`, and `H3_VERSION_PATCH` macros.

## API preconditions

The H3 API expects valid input. Behavior of the library may be undefined when given invalid input. Indexes should be validated with `isValidCell` or `isValidDirectedEdge` as appropriate.

The library attempts to validate inputs and return useful error codes if input is invalid. Which inputs are validated, and how precisely they are
validated, may change between versions of the library. As a result the specific error code returned may change.

## Function renaming

The [`H3_PREFIX`](./compilation-options#H3_PREFIX) exists to rename all functions in the H3 public API with a prefix chosen at compile time. The default is to have no prefix.
This can be needed when linking multiple copies of the H3 library in order to avoid naming collisions. Internal functions and symbols are not renamed.

# === highlights/aggregation ===

---

id: aggregation
title: Aggregation
sidebar_label: Aggregation
slug: /highlights/aggregation

---

Analysis of location data, such as locations of cars in a city, can be done by bucketing locations. ([Sahr et al., 2003](http://webpages.sou.edu/~sahrk/sqspc/pubs/gdggs03.pdf)) Using a regular grid provides smooth gradients and the ability to measure differences between cells.

The cell shape of that grid system is an important consideration. For simplicity, it should be a polygon that tiles regularly: the triangle, the square, or the hexagon. Of these, triangles and squares have neighbors with different distances. Triangles have three different distances, and squares have two different distances. For hexagons, all neighbors are equidistant.

| Triangle                                                             | Square                                                             | Hexagon                                                             |
| -------------------------------------------------------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------- |
| <img src="/images/neighbors-triangle.png" style={{width:'400px'}} /> | <img src="/images/neighbors-square.png" style={{width:'400px'}} /> | <img src="/images/neighbors-hexagon.png" style={{width:'400px'}} /> |
| Triangles have 12 neighbors                                          | Squares have 8 neighbors                                           | Hexagons have 6 neighbors                                           |

This property allows for simpler analysis of movement. Hexagons have the property of expanding rings of neighbors approximating circles:

<div align="center">
  <img src="/images/neighbors.png" style={{width:'400px'}} /><br />
  <i>All six neighbors of a hexagon (ring 1)</i>
</div>

Hexagons are also optimally space-filling. On average, a polygon may be filled with hexagon tiles with a smaller margin of error than would be present with square tiles.

## References

- Use case: [H3: Uber’s Hexagonal Hierarchical Spatial Index ](https://www.uber.com/en-GB/blog/h3/)
- Observable notebook example: [Intro to h3-js](https://observablehq.com/@nrabinowitz/h3-tutorial-the-h3-js-library?collection=@nrabinowitz/h3-tutorial)
- Jupyter notebook example: [H3 Python API](https://github.com/uber/h3-py-notebooks/blob/master/notebooks/usage.ipynb)

# === highlights/flowmodel ===

---

id: flowmodel
title: Flow Modelling
sidebar_label: Flow Modelling
slug: /highlights/flowmodel

---

H3's hexagonal grid is well suited to analyzing movement. In addition to the benefits of the hexagonal grid shape, H3 includes other features for modelling flow.

H3 can create indexes that refer to the movement from one cell to a neighbor. These directed edge indexes share the advantages with their cell index counterparts, such as being 64 bit integers. The use of directed edges makes it possible to associate a weight with a movement in the grid.

(A planned improvement for the H3 system is to create indexes that refer to the edge between two cells without regards of direction.)

## Links

- Observable notebook example: [H3 Travel Times](https://observablehq.com/@nrabinowitz/h3-travel-times)

# === highlights/indexing ===

---

id: indexing
title: Indexing
sidebar_label: Indexing
slug: /highlights/indexing

---

H3 is a hierarchical geospatial index. H3 indexes refer to cells by the spatial hierarchy. Every hexagonal cell, up to the maximum resolution supported by H3, has seven child cells below it in this hierarchy. This subdivision is referred to as _aperture 7_.

<div align="center">
  <img src="/images/parent-child.png" style={{width:'400px'}} /><br />
  <i>A parent hexagon approximately contains seven children</i>
</div>

Hexagons do not cleanly subdivide into seven finer hexagons. However, by alternating the orientation of grids a subdivision into seven cells can be approximated. This makes it possible to truncate the precision within a fixed margin of error of an H3 index. It is also possible to determine all the children of a parent H3 index.

Approximate containment only applies when truncating the precision of an H3 index. The borders of hexagons indexed at a specific resolution are not approximate and not affected by these considerations. For example, indexing points to cells at a certain resolution and finding those cell's neighbors is not affected by approximate containment.

While geographic containment is approximate, logical containment in the index is exact. It is possible to use H3 as an exact logical index on top of data indexed at a specific resolution.

This approximation allows for efficiently relating datasets indexed at different resolutions of the H3 grid. The functions for changing precision (`h3ToParent`, `h3ToChildren`) are implemented with only a few bitwise operations, making them very fast. The structure of the H3 index means that geographically close locations will tend to have numerically close indexes.

The hierarchical structure can also be used in analysis, when the precision or uncertainty for a location needs to be encoded in the spatial index. For example, a point from a GPS receiver could be indexed at a coarser resolution when the precision of the signal is lower, or some cells could be aggregated to a parent cell when there are too few data points in each of the finer cells.

Hierarchical containment allows for use cases like making contiguous sets of cells "compact" with `compactCells`. It is then possible to `uncompactCells` to the same input set of cells, or to test whether a cell is contained by the compact set.

| Uncompacted (dense)                                                    | Compacted (sparse)                                                 |
| ---------------------------------------------------------------------- | ------------------------------------------------------------------ |
| <img src="/images/ca_uncompact_6_10633.png" style={{width:'500px'}} /> | <img src="/images/ca_compact_6_901.png" style={{width:'500px'}} /> |
| California represented by 10633 uncompacted cells                      | California represented by 901 compacted cells                      |

In use cases where exact boundaries are needed applications must take care to handle the hierarchical concerns. This can be done by taking care to use the hierarchy as a logical one rather than geographic. Another useful approach is using the grid system as an optimization in addition to a more precise point-in-polygon check.

## Links

- Observable notebook example: [H3 Hierarchical (Non)Containment](https://observablehq.com/@nrabinowitz/h3-hierarchical-non-containment?collection=@nrabinowitz/h3)
- Observable notebook example: [Shape simplification with H3](https://observablehq.com/@nrabinowitz/shape-simplification-with-h3?collection=@nrabinowitz/h3)

# === highlights/joining ===

---

id: joining
title: Joining
sidebar_label: Joining
slug: /highlights/joining

---

H3, acting as a standard unit of analysis, can be used to join disparate data sets.

The H3 library contains support for indexing points, lines, and regions into the grid. Other data formats, such as rasters, can be indexed into H3 using combinations of these basic indexing operations. Once data is indexed into H3 indexes, it can be easily joined with other datasets on the H3 index.

## References

- Example: [Placekey](https://www.placekey.io/)
- Jupyter notebook example: [Unified Data Layers](https://github.com/uber/h3-py-notebooks/blob/master/notebooks/unified_data_layers.ipynb)
- Observable notebook example: [Suitability Analysis](https://observablehq.com/@nrabinowitz/h3-tutorial-suitability-analysis?collection=@nrabinowitz/h3-tutorial)

# === highlights/ml ===

---

id: ml
title: Machine Learning
sidebar_label: Machine Learning
slug: /highlights/ml

---

H3 is well suited to applying machine learning to geospatial data. Techniques from computer vision, such as [convolution](https://medium.com/@RaghavPrabhu/understanding-of-convolutional-neural-network-cnn-deep-learning-99760835f148#:~:text=Convolution%20is%20the%20first%20layer,and%20a%20filter%20or%20kernel), can be applied to the pixel grid defined by H3.

H3 has functions for finding neighbors (`kRing`) for use in performing convolution, and functions for transforming indexes to a two dimensional IJ coordinate space on which other computer vision algorithms can be run.

## Links

- Jupyter notebook example: [Uber H3 API examples on Urban Analytics in the city of Toulouse (France)](https://github.com/uber/h3-py-notebooks/blob/master/notebooks/urban_analytics.ipynb)

# === installation ===

---

id: installation
title: Installation
sidebar_label: Installation
slug: /installation

# when updating this file with a new version number, do a search and replace

# for all instances.

---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

We recommend using prebuilt [bindings](/docs/community/bindings) if they are available for your programming language. Bindings for Go, Java, JavaScript, Python, and others are available.

## Package managers

<Tabs
groupId="env"
defaultValue="python"
values={[
{label: 'Python', value: 'python'},
{label: 'Java', value: 'java'},
{label: 'JavaScript', value: 'javascript'},
{label: 'Homebrew', value: 'brew'},
{label: 'DuckDB', value: 'duckdb'},
]
}>
<TabItem value="python">

Using [PyPi](https://pypi.org/project/h3/), run:

```bash
pip install h3
```

Using [Conda](https://github.com/conda-forge/h3-py-feedstock), run:

```
conda config --add channels conda-forge
conda install h3-py
```

</TabItem>
<TabItem value="java">

Using Maven, add the following to your `pom.xml` file:

```xml
<dependency>
    <groupId>com.uber</groupId>
    <artifactId>h3</artifactId>
    <version>4.3.0</version>
</dependency>
```

Using Gradle, add the following to your build script:

```gradle
compile("com.uber:h3:4.3.0")
```

</TabItem>
<TabItem value="javascript">

Using npm, run:

```bash
npm install h3-js
```

Using yarn, run:

```bash
yarn add h3-js
```

</TabItem>
<TabItem value="brew">

Using brew, run:

```bash
brew install h3
```

This installs the C library and filter applications.

</TabItem>
<TabItem value="duckdb">

Using DuckDB, run this to install the [H3 extension](https://duckdb.org/community_extensions/extensions/h3.html):

```sql
INSTALL h3 FROM community;
```

Once installed, the extension can be loaded with:

```sql
LOAD h3;
```

</TabItem>
</Tabs>

## Install from source

First, clone the repository or [download the source](https://github.com/uber/h3)
and check out the latest release:

```bash
git clone https://github.com/uber/h3.git
cd h3
git checkout v$(<VERSION)
```

Note: You must install build dependencies for your operating system.

<Tabs
groupId="os"
defaultValue="macos"
values={[
{label: 'mac OS', value: 'macos'},
{label: 'alpine', value: 'alpine'},
{label: 'Debian/Ubuntu', value: 'debian'},
{label: 'Windows', value: 'windows'},
{label: 'FreeBSD', value: 'freebsd'},
]
}>
<TabItem value="macos">

First make sure you [have the developer tools installed](http://osxdaily.com/2014/02/12/install-command-line-tools-mac-os-x/) and then run:

```bash
# Installing the bare build requirements
brew install cmake
# Installing useful tools for development
brew install clang-format lcov doxygen
```

</TabItem>
<TabItem value="alpine">

```bash
# Installing the bare build requirements
apk add cmake make gcc libtool musl-dev
```

</TabItem>
<TabItem value="debian">

```bash
# Installing the bare build requirements
sudo apt install cmake make gcc libtool
# Installing useful tools for development
sudo apt install clang-format cmake-curses-gui lcov doxygen
```

</TabItem>
<TabItem value="windows">

You need to install CMake and Visual Studio, including the Visual C++ compiler. We recommend Visual Studio 2017 or later.

:::info

You can build H3 as a shared library (DLL) on Windows, but the test suite does not support this configuration because the tests use functions internal to the DLL, and they are not exposed for testing.

:::

</TabItem>
<TabItem value="freebsd">

```bash
# Installing the build requirements
sudo pkg install bash cmake gmake doxygen lcov
```

</TabItem>
</Tabs>

Next, build the library:

```bash
mkdir build
cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
cmake --build .
```

Optionally, to run H3's test suite, run:

```
ctest
```

By default, the filter applications are built when you build H3. Confirm they are working by running:

```
./bin/latLngToCell --lat 14 --lng -42 --resolution 2
```

# === library/errors ===

---

id: errors
title: Error handling
sidebar_label: Error handling
slug: /library/errors

---

H3 does it's best to be robust to system failures or unexpected inputs, but
some times these cannot be recovered from. H3's way of doing this is to return
an error code to the caller.

## Example

This code example checks for an error when calling an H3 function and prints a message if the call did not succeed:

```c
H3Error err;
H3Index result;

err = latLngToCell(lat, lng, res, &result);
if (err) {
    fprintf(stderr, "Error: %d", err);
}
```

## H3Error type

The type returned by most H3 functions is `H3Error`, a 32 bit integer type with the following properties:

- `H3Error` will be an integer type of 32 bits, i.e. `uint32_t`.
- `H3Error` with value 0 indicates success (no error).
- No `H3Error` value will set the most significant bit.
- As a result of these properties, no `H3Error` value will set the bits that correspond with the **Mode** bit field in an `H3Index`.

32 bit return codes with the high bit never set allows for mixing error codes and resulting indexes if desired by the application, after copying the error codes into the result buffer.

## Table of error codes

| Value | Name                 | Description                                                                                 |
| ----- | -------------------- | ------------------------------------------------------------------------------------------- |
| 0     | E_SUCCESS            | Success (no error)                                                                          |
| 1     | E_FAILED             | The operation failed but a more specific error is not available                             |
| 2     | E_DOMAIN             | Argument was outside of acceptable range (when a more specific error code is not available) |
| 3     | E_LATLNG_DOMAIN      | Latitude or longitude arguments were outside of acceptable range                            |
| 4     | E_RES_DOMAIN         | Resolution argument was outside of acceptable range                                         |
| 5     | E_CELL_INVALID       | `H3Index` cell argument was not valid                                                       |
| 6     | E_DIR_EDGE_INVALID   | `H3Index` directed edge argument was not valid                                              |
| 7     | E_UNDIR_EDGE_INVALID | `H3Index` undirected edge argument was not valid                                            |
| 8     | E_VERTEX_INVALID     | `H3Index` vertex argument was not valid                                                     |
| 9     | E_PENTAGON           | Pentagon distortion was encountered which the algorithm could not handle it                 |
| 10    | E_DUPLICATE_INPUT    | Duplicate input was encountered in the arguments and the algorithm could not handle it      |
| 11    | E_NOT_NEIGHBORS      | `H3Index` cell arguments were not neighbors                                                 |
| 12    | E_RES_MISMATCH       | `H3Index` cell arguments had incompatible resolutions                                       |
| 13    | E_MEMORY_ALLOC       | Necessary memory allocation failed                                                          |
| 14    | E_MEMORY_BOUNDS      | Bounds of provided memory were not large enough                                             |
| 15    | E_OPTION_INVALID     | Mode or flags argument was not valid                                                        |
| 16    | E_INDEX_INVALID      | `H3Index` argument was not valid                                                            |
| 17    | E_BASE_CELL_DOMAIN   | Base cell number was outside of acceptable range                                            |
| 18    | E_DIGIT_DOMAIN       | Child indexing digits invalid                                                               |
| 19    | E_DELETED_DIGIT      | Child indexing digits refer to a deleted subsequence                                        |

The H3 library may always add additional error messages. Error messages not recognized by the application should be treated as `E_FAILED`.

The C library has a value `H3_ERROR_END` which is one past the last defined error message. This is for convenience when iterating over error messages.

### Bindings

Bindings translate error codes into the error handling mechanism appropriate to their language. For example, Java will convert error codes into Java Exceptions.

When possible, it is preferable to retain the error code. When this is not possible it is fine to elide them. Language bindings should include error messages that are formatted as is usual in their language.

## References

- [Technical RFC on error handling](https://github.com/uber/h3/blob/master/dev-docs/RFCs/v4.0.0/error-handling-rfc.md)

# === library/index/cell ===

---

id: cell
title: Cell mode
sidebar_label: Cell mode
slug: /library/index/cell

---

<div align="center">
  <img height="300" src="/images/cell_mode.png" />
</div>

The H3 system assigns a unique hierarchical index to each cell. The H3 index of a resolution _r_ cell begins with the appropriate resolution 0 base cell number. This is followed by a sequence of _r_ digits 0-6, where each _i_<sup>th</sup> digit _d_<sub>i</sub> specifies one of the 7 cells centered on the cell indicated by the coarser resolution digits _d_<sub>1</sub> through _d_<sub>i-1</sub>. A local hexagon coordinate system is assigned to each of the resolution 0 base cells and is used to orient all hierarchical indexing child cells of that base cell. The assignment of digits 0-6 at each resolution uses a _Central Place Indexing_ arrangement (see [Sahr, 2014](http://webpages.sou.edu/~sahrk/sqspc/pubs/autocarto14.pdf)). In the case of the 12 pentagonal cells the indexing hierarchy produced by sub-digit 1 is removed at all resolutions.

Child hexagons are linearly smaller than their parent hexagons.

<div align="center">
  <img height="300" src="/images/cpidigits.png" />
</div>

## H3 Cell Index

An H3 Cell index (mode 1) represents a cell (hexagon or pentagon) in the H3 grid system at a particular resolution. The components of the H3 Cell index are packed into a 64-bit integer in order, highest bit first, as follows:

- 1 bit reserved and set to 0,
- 4 bits to indicate the H3 Cell index mode,
- 3 bits reserved and set to 0,
- 4 bits to indicate the cell resolution 0-15,
- 7 bits to indicate the base cell 0-121,
- 3 bits to indicate each subsequent digit 0-6 from resolution 1 up to the resolution of the cell (45 bits total are reserved for resolutions 1-15)

The three bits for each unused digit are set to 7.

## Bit layout of H3Index for cells

The layout of an `H3Index` is shown below in table form. The interpretation of the "Mode-Dependent" field differs depending on the mode of the index.

<table>
<tr>
  <th></th>
  <th>0x0F</th>
  <th>0x0E</th>
  <th>0x0D</th>
  <th>0x0C</th>
  <th>0x0B</th>
  <th>0x0A</th>
  <th>0x09</th>
  <th>0x08</th>
  <th>0x07</th>
  <th>0x06</th>
  <th>0x05</th>
  <th>0x04</th>
  <th>0x03</th>
  <th>0x02</th>
  <th>0x01</th>
  <th>0x00</th>
</tr>
<tr>
  <th>0x30</th>
  <td>Reserved (0)</td>
  <td colspan="4">Mode (1)</td>
  <td colspan="3">Reserved (0)</td>
  <td colspan="4">Resolution</td>
  <td colspan="4">Base cell</td>
</tr>
<tr>
  <th>0x20</th>
  <td colspan="3">Base cell</td>
  <td colspan="3">Digit 1</td>
  <td colspan="3">Digit 2</td>
  <td colspan="3">Digit 3</td>
  <td colspan="3">Digit 4</td>
  <td>Digit 5</td>
</tr>
<tr>
  <th>0x10</th>
  <td colspan="2">Digit 5</td>
  <td colspan="3">Digit 6</td>
  <td colspan="3">Digit 7</td>
  <td colspan="3">Digit 8</td>
  <td colspan="3">Digit 9</td>
  <td colspan="2">Digit 10</td>
</tr>
<tr>
  <th>0x00</th>
  <td>Digit 10</td>
  <td colspan="3">Digit 11</td>
  <td colspan="3">Digit 12</td>
  <td colspan="3">Digit 13</td>
  <td colspan="3">Digit 14</td>
  <td colspan="3">Digit 15</td>
</tr>
</table>

## Links

- Observable notebook example: [H3 Index Inspector](https://observablehq.com/@nrabinowitz/h3-index-inspector?collection=@nrabinowitz/h3)

# === library/index/directededge ===

---

id: directededge
title: Directed edge mode
sidebar_label: Directed edge mode
slug: /library/index/directededge

---

<div align="center">
  <img height="300" src="/images/edge_mode.png" />
</div>

An H3 Directed Edge index (mode 2) represents a single directed edge between two cells (an "origin" cell and a neighboring "destination" cell). The components of the H3 Directed Edge index are packed into a 64-bit integer in order, highest bit first, as follows:

- 1 bit reserved and set to 0,
- 4 bits to indicate the H3 Unidirectional Edge index mode,
- 3 bits to indicate the edge (1-6) of the origin cell,
- Subsequent bits matching the index bits of the [origin cell](./cell#h3-cell-index).

## Bit layout of H3Index for directed edges

The layout of an `H3Index` is shown below in table form. The interpretation of the "Mode-Dependent" field differs depending on the mode of the index.

<table>
<tr>
  <th></th>
  <th>0x0F</th>
  <th>0x0E</th>
  <th>0x0D</th>
  <th>0x0C</th>
  <th>0x0B</th>
  <th>0x0A</th>
  <th>0x09</th>
  <th>0x08</th>
  <th>0x07</th>
  <th>0x06</th>
  <th>0x05</th>
  <th>0x04</th>
  <th>0x03</th>
  <th>0x02</th>
  <th>0x01</th>
  <th>0x00</th>
</tr>
<tr>
  <th>0x30</th>
  <td>Reserved (0)</td>
  <td colspan="4">Mode (2)</td>
  <td colspan="3">Edge</td>
  <td colspan="4">Resolution</td>
  <td colspan="4">Base cell</td>
</tr>
<tr>
  <th>0x20</th>
  <td colspan="3">Base cell</td>
  <td colspan="3">Digit 1</td>
  <td colspan="3">Digit 2</td>
  <td colspan="3">Digit 3</td>
  <td colspan="3">Digit 4</td>
  <td>Digit 5</td>
</tr>
<tr>
  <th>0x10</th>
  <td colspan="2">Digit 5</td>
  <td colspan="3">Digit 6</td>
  <td colspan="3">Digit 7</td>
  <td colspan="3">Digit 8</td>
  <td colspan="3">Digit 9</td>
  <td colspan="2">Digit 10</td>
</tr>
<tr>
  <th>0x00</th>
  <td>Digit 10</td>
  <td colspan="3">Digit 11</td>
  <td colspan="3">Digit 12</td>
  <td colspan="3">Digit 13</td>
  <td colspan="3">Digit 14</td>
  <td colspan="3">Digit 15</td>
</tr>
</table>

# === library/index/h3indexing ===

---

id: h3Indexing
title: H3 Index
sidebar_label: H3 Index
slug: /core-library/h3Indexing

---

## Introduction

The H3 system assigns a unique hierarchical index to each cell. Each directed edge and vertex is assigned an index based on its origin or owner cell, respectively.

## H3Index Representation

An `H3Index` is the 64-bit integer representation of an H3 index, which may be one of multiple modes to indicate the concept being indexed.

- Mode 0 is reserved and indicates an [invalid H3 index](#invalid-index).
- Mode 1 is an _[H3 Cell](../library/index/cell)_ (Hexagon/Pentagon) index.
- Mode 2 is an _[H3 Directed Edge](../library/index/directededge)_ (Cell A -> Cell B) index.
- Mode 3 is planned to be a bidirectional edge (Cell A <-> Cell B).
- Mode 4 is an _[H3 Vertex](../library/index/vertex)_ (i.e. a single vertex of an H3 Cell).

The canonical string representation of an `H3Index` is the hexadecimal representation of the integer, using lowercase letters. The string representation is variable length (no zero padding) and is not prefixed or suffixed.

### Invalid Index

Mode 0 contains a special index, `H3_NULL`, which is unique: it is bit-equivalent to `0`.
This index indicates, _specifically_, an invalid, missing, or uninitialized H3 index;
it is analogous to `NaN` in floating point.
It should be used instead of an arbitrary Mode 0 index, due to its uniqueness and easy identifiability.
A mode 0 index could also indicate an [error code](../library/errors) has been provided instead of a valid H3 index.

## Bit layout of H3Index

The layout of an `H3Index` is shown below in table form. The interpretation of the "Mode-Dependent" field differs depending on the mode of the index.

<table>
<tr>
  <th></th>
  <th>0x0F</th>
  <th>0x0E</th>
  <th>0x0D</th>
  <th>0x0C</th>
  <th>0x0B</th>
  <th>0x0A</th>
  <th>0x09</th>
  <th>0x08</th>
  <th>0x07</th>
  <th>0x06</th>
  <th>0x05</th>
  <th>0x04</th>
  <th>0x03</th>
  <th>0x02</th>
  <th>0x01</th>
  <th>0x00</th>
</tr>
<tr>
  <th>0x30</th>
  <td>Reserved</td>
  <td colspan="4">Mode</td>
  <td colspan="3">Mode-Dependent</td>
  <td colspan="4">Resolution</td>
  <td colspan="4">Base cell</td>
</tr>
<tr>
  <th>0x20</th>
  <td colspan="3">Base cell</td>
  <td colspan="3">Digit 1</td>
  <td colspan="3">Digit 2</td>
  <td colspan="3">Digit 3</td>
  <td colspan="3">Digit 4</td>
  <td>Digit 5</td>
</tr>
<tr>
  <th>0x10</th>
  <td colspan="2">Digit 5</td>
  <td colspan="3">Digit 6</td>
  <td colspan="3">Digit 7</td>
  <td colspan="3">Digit 8</td>
  <td colspan="3">Digit 9</td>
  <td colspan="2">Digit 10</td>
</tr>
<tr>
  <th>0x00</th>
  <td>Digit 10</td>
  <td colspan="3">Digit 11</td>
  <td colspan="3">Digit 12</td>
  <td colspan="3">Digit 13</td>
  <td colspan="3">Digit 14</td>
  <td colspan="3">Digit 15</td>
</tr>
</table>

## Links

- Observable notebook example: [H3 Index Bit Layout](https://observablehq.com/@nrabinowitz/h3-index-bit-layout?collection=@nrabinowitz/h3)

# === library/index/vertex ===

---

id: vertex
title: Vertex mode
sidebar_label: Vertex mode
slug: /library/index/vertex

---

<div align="center">
  <img height="300" src="/images/vertex_mode.png" />
</div>

An H3 Vertex index (mode 4) represents a single topological vertex in H3 grid system, shared by three cells. Note that this does not include the distortion vertexes occasionally present in a cell's geographic boundary. An H3 Vertex is arbitrarily assigned one of the three neighboring cells as its "owner", which is used to calculate the canonical index and geographic coordinates for the vertex. The components of the H3 Vertex index are packed into a 64-bit integer in order, highest bit first, as follows:

- 1 bit reserved and set to 0,
- 4 bits to indicate the H3 Vertex index mode,
- 3 bits to indicate the vertex number (0-5) of vertex on the owner cell,
- Subsequent bits matching the index bits of the [owner cell](./cell#h3-cell-index).

## Bit layout of H3Index for vertexes

The layout of an `H3Index` for vertexes is shown below in table form. The interpretation of the "Mode-Dependent" field differs depending on the mode of the index.

<table>
<tr>
  <th></th>
  <th>0x0F</th>
  <th>0x0E</th>
  <th>0x0D</th>
  <th>0x0C</th>
  <th>0x0B</th>
  <th>0x0A</th>
  <th>0x09</th>
  <th>0x08</th>
  <th>0x07</th>
  <th>0x06</th>
  <th>0x05</th>
  <th>0x04</th>
  <th>0x03</th>
  <th>0x02</th>
  <th>0x01</th>
  <th>0x00</th>
</tr>
<tr>
  <th>0x30</th>
  <td>Reserved (0)</td>
  <td colspan="4">Mode (4)</td>
  <td colspan="3">Vertex</td>
  <td colspan="4">Resolution</td>
  <td colspan="4">Base cell</td>
</tr>
<tr>
  <th>0x20</th>
  <td colspan="3">Base cell</td>
  <td colspan="3">Digit 1</td>
  <td colspan="3">Digit 2</td>
  <td colspan="3">Digit 3</td>
  <td colspan="3">Digit 4</td>
  <td>Digit 5</td>
</tr>
<tr>
  <th>0x10</th>
  <td colspan="2">Digit 5</td>
  <td colspan="3">Digit 6</td>
  <td colspan="3">Digit 7</td>
  <td colspan="3">Digit 8</td>
  <td colspan="3">Digit 9</td>
  <td colspan="2">Digit 10</td>
</tr>
<tr>
  <th>0x00</th>
  <td>Digit 10</td>
  <td colspan="3">Digit 11</td>
  <td colspan="3">Digit 12</td>
  <td colspan="3">Digit 13</td>
  <td colspan="3">Digit 14</td>
  <td colspan="3">Digit 15</td>
</tr>
</table>

# === library/migrating-3.x ===

---

id: migrating-3.x
title: Migrating from H3 version 3.x
sidebar_label: Migration guide
slug: /library/migrating-3.x

---

The H3 library introduced breaking changes in version 4.0.0, so applications developed against earlier versions
need to be updated before they can use the new library version. Most of the changes relate to function naming,
and some relate to the behavior of the functions.

The grid itself - the layout of cells, which cell an H3 index refers to, and the structure of an H3 index - is
not changed in 4.0.0. H3 indexes generated by 3.x will be understood the same by 4.0.0, and those generated by 4.0.0
will be understood the same in 3.x.

The areas where there are changes include:

# Function naming

Many [function names have changed](./migration-3.x/functions.md) between 3.x and 4.0.0. These follow the H3 [terminology](./terminology.md) reference,
and that document explains how each function name has been renamed. These changes were made to make the API more
consistent and predictable.

# Error codes

The C library is being changed to more consistently [report errors](./errors.md). This is done via the return code of
functions. Users of the C library will need to adjust some function calls to pass output parameters instead of
using the return value of a function.

# === library/migration-3.x/functions ===

---

id: functions
title: Function name changes
sidebar_label: Function name changes
slug: /library/migration-3.x/functions

---

The following function and structure names changed from 3.x to 4.0.0:

### General Function Names

| 3.x name.                     | 4.0.0 name            |
| ----------------------------- | --------------------- |
| _Does Not Exist (DNE)_        | `isValidIndex`        |
| `h3IsValid`                   | `isValidCell`         |
| `h3UnidirectionalEdgeIsValid` | `isValidDirectedEdge` |
| `h3IsPentagon`                | `isPentagon`          |
| `h3IsResClassIII`             | `isResClassIII`       |
| `h3IndexesAreNeighbors`       | `areNeighborCells`    |
| `h3ToParent`                  | `cellToParent`        |
| `h3ToCenterChild`             | `cellToCenterChild`   |
| `h3ToChildren`                | `cellToChildren`      |
| `numHexagons`                 | `getNumCells`         |
| `getRes0Indexes`              | `getRes0Cells`        |
| `getPentagonIndexes`          | `getPentagons`        |
| `h3GetBaseCell`               | `getBaseCellNumber`   |
| `h3GetResolution`             | `getResolution`       |
| _DNE_                         | `getMode`             |
| `h3GetFaces`                  | `getIcosahedronFaces` |
| `geoToH3`                     | `latLngToCell`        |
| `h3ToGeo`                     | `cellToLatLng`        |
| `compact`                     | `compactCells`        |
| `uncompact`                   | `uncompactCells`      |
| `polyfill`                    | `polygonToCells`      |

**Note**: `getResolution` and `getBaseCellNumber` should work for both cells and edges.

### H3 Grid Functions

Many of these functions will have three forms:

- `<func_name>`
- `<func_name>Unsafe`
- `<func_name>Safe`

The `Unsafe` version is fast, but may fail if it encounters a pentagon.
It should return a failure code in this case.

The `Safe` version is slower, but will work in all cases.

The version without either suffix is intended to be the one typically
used.
This version will first attempt the `Unsafe` version, and if
it detects failure, will fall back to the `Safe` version.
Encountering pentagons is rare in most use-cases, so this version
should usually be equivalent to the fast version, but with a guarantee
that it will not fail.

Initially, we **will not** expose the `Safe` versions to users in the API.
We may expose them in the future if a need becomes clear.

#### Distance

| 3.x name.    | 4.0.0 name              |
| ------------ | ----------------------- |
| `h3Distance` | `gridDistance`          |
| `h3Line`     | `gridPathCells`         |
| _DNE_        | `gridPathEdges`         |
| _DNE_        | `gridPathDirectedEdges` |

#### Filled-In Disk With Distances

| 3.x name.           | 4.0.0 name                | Calls                                 |
| ------------------- | ------------------------- | ------------------------------------- |
| `hexRangeDistances` | `gridDiskDistancesUnsafe` | NONE                                  |
| `_kRingInternal`    | `gridDiskDistancesSafe`   | NONE                                  |
| `kRingDistances`    | `gridDiskDistances`       | `hexRangeDistances`, `_kRingInternal` |

#### Filled-In Disk Without Distances

| 3.x name.   | 4.0.0 name        | Calls               |
| ----------- | ----------------- | ------------------- |
| `hexRange`  | `gridDiskUnsafe`  | `hexRangeDistances` |
| _DNE_       | `gridDiskSafe`    |                     |
| `kRing`     | `gridDisk`        | `kRingDistances`    |
| `hexRanges` | `gridDisksUnsafe` | N x `hexRange`      |

#### Hollow Ring

| 3.x name. | 4.0.0 name       | Calls                            |
| --------- | ---------------- | -------------------------------- |
| `hexRing` | `gridRingUnsafe` | NONE                             |
| _DNE_     | `gridRingSafe`   | `gridDiskDistancesSafe`          |
| _DNE_     | `gridRing`       | `gridRingUnsafe`, `gridRingSafe` |

#### Local IJ

| 3.x name                  | 4.0.0 name      |
| ------------------------- | --------------- |
| `experimentalLocalIjToH3` | `localIjToCell` |
| `experimentalH3ToLocalIj` | `cellToLocalIj` |

### H3 Edge Types

Instead of `UnidirectionalEdge`, use the term `DirectedEdge`.

For a future undirected edge mode, use the term `Edge`.

| 3.x name.                                     | 4.0.0 name                   |
| --------------------------------------------- | ---------------------------- |
| `h3UnidirectionalEdgeIsValid`                 | `isValidDirectedEdge`        |
| `getH3UnidirectionalEdge`                     | `cellsToDirectedEdge`        |
| `getH3IndexesFromUnidirectionalEdge`          | `directedEdgeToCells`        |
| `getH3UnidirectionalEdgesFromHexagon`         | `originToDirectedEdges`      |
| _DNE_                                         | `destinationToDirectedEdges` |
| `getH3UnidirectionalEdgeBoundary`             | `directedEdgeToBoundary`     |
| `getOriginH3IndexFromUnidirectionalEdge`      | `getDirectedEdgeOrigin`      |
| `getDestinationH3IndexFromUnidirectionalEdge` | `getDirectedEdgeDestination` |

### Area/Length Functions

| 3.x name.             | 4.0.0 name                  |
| --------------------- | --------------------------- |
| `hexAreaKm2`          | `getHexagonAreaAvgKm2`      |
| `hexAreaM2`           | `getHexagonAreaAvgM2`       |
| `edgeLengthKm`        | `getHexagonEdgeLengthAvgKm` |
| `edgeLengthM`         | `getHexagonEdgeLengthAvgM`  |
| _DNE_                 | `getPentagonAreaAvg*`       |
| _DNE_                 | `getPentagonEdgeLengthAvg*` |
| _DNE_                 | `cellAreaKm2`               |
| _DNE_                 | `cellAreaM2`                |
| `pointDistKm`         | `greatCircleDistanceKm`     |
| `pointDistM`          | `greatCircleDistanceM`      |
| `pointDistRads`       | `greatCircleDistanceRads`   |
| `exactEdgeLengthRads` | `edgeLengthRads`            |
| `exactEdgeLengthKm`   | `edgeLengthKm`              |
| `exactEdgeLengthM`    | `edgeLengthM`               |

**Note**: `cellAreaKm2` and `cellAreaM2` would return the actual area of
the passed-in cell.

## Polygons

### Data Structures

- rename `GeoBoundary` to `CellBoundary` to indicate it is space-limited to describing the geometry of cells

| 3.x name          | 4.0.0 name        | Notes                           |
| ----------------- | ----------------- | ------------------------------- |
| `GeoBoundary`     | `CellBoundary`    | <= 10 stack-allocated `LatLng`s |
| `GeoCoord`        | `LatLng`          |                                 |
| `Geofence`        | `GeoLoop`         | heap-allocated `LatLng`s        |
| `GeoPolygon`      | `GeoPolygon`      |                                 |
| `GeoMultiPolygon` | `GeoMultiPolygon` | currently not used              |

### Functions

| 3.x name                          | 4.0.0 name                  | Notes                      |
| --------------------------------- | --------------------------- | -------------------------- |
| `h3ToGeoBoundary`                 | `cellToBoundary`            | returns `CellBoundary`     |
| _DNE_                             | `cellToLoop`                | returns `GeoLoop`          |
| _DNE_                             | `loopToBoundary`            |                            |
| _DNE_                             | `boundaryToLoop`            |                            |
| `getH3UnidirectionalEdgeBoundary` | `directedEdgeToBoundary`    | returns `CellBoundary`     |
| `h3SetToLinkedGeo`                | `cellsToLinkedMultiPolygon` | returns `LinkedGeoPolygon` |
| `h3SetToMultiPolygon`             | `cellsToMultiPolygon`       | bindings only              |

# === library/restable ===

---

id: restable
title: Tables of Cell Statistics Across Resolutions
sidebar_label: Tables of cell stats
slug: /core-library/restable

---

## Cell counts

We list the number of hexagons and pentagons at each H3 resolution.
[There are always exactly $12$ pentagons at every resolution](../core-library/overview.md).

| Res | Total number of cells |  Number of hexagons | Number of pentagons |
| --: | --------------------: | ------------------: | ------------------: |
|   0 |                   122 |                 110 |                  12 |
|   1 |                   842 |                 830 |                  12 |
|   2 |                 5,882 |               5,870 |                  12 |
|   3 |                41,162 |              41,150 |                  12 |
|   4 |               288,122 |             288,110 |                  12 |
|   5 |             2,016,842 |           2,016,830 |                  12 |
|   6 |            14,117,882 |          14,117,870 |                  12 |
|   7 |            98,825,162 |          98,825,150 |                  12 |
|   8 |           691,776,122 |         691,776,110 |                  12 |
|   9 |         4,842,432,842 |       4,842,432,830 |                  12 |
|  10 |        33,897,029,882 |      33,897,029,870 |                  12 |
|  11 |       237,279,209,162 |     237,279,209,150 |                  12 |
|  12 |     1,660,954,464,122 |   1,660,954,464,110 |                  12 |
|  13 |    11,626,681,248,842 |  11,626,681,248,830 |                  12 |
|  14 |    81,386,768,741,882 |  81,386,768,741,870 |                  12 |
|  15 |   569,707,381,193,162 | 569,707,381,193,150 |                  12 |

## Cell areas

:::caution
Cell areas are computed with a **spherical** model of the earth using the
[authalic radius](https://en.wikipedia.org/wiki/Earth_radius#Authalic_radius)
given by
[WGS84](https://en.wikipedia.org/wiki/WGS84)/[EPSG:4326](https://epsg.io/4326).
:::

### Average area in km<sup>2</sup>

The area of an H3 cell varies based on its position relative to the
[icosahedron vertices](../core-library/overview.md).
We show the **average** hexagon areas for each resolution.
All pentagons within a resolution have the same area.

| Res | Average <ins>Hexagon</ins> Area (km<sup>2</sup>) | Pentagon Area\* (km<sup>2</sup>) | Ratio (P/H) |
| --: | -----------------------------------------------: | -------------------------------: | ----------: |
|   0 |                              4,357,449.416078381 |              2,562,182.162955496 |      0.5880 |
|   1 |                                609,788.441794133 |                328,434.586246469 |      0.5386 |
|   2 |                                 86,801.780398997 |                 44,930.898497879 |      0.5176 |
|   3 |                                 12,393.434655088 |                  6,315.472267516 |      0.5096 |
|   4 |                                  1,770.347654491 |                    896.582383141 |      0.5064 |
|   5 |                                    252.903858182 |                    127.785583023 |      0.5053 |
|   6 |                                     36.129062164 |                     18.238749548 |      0.5048 |
|   7 |                                      5.161293360 |                      2.604669397 |      0.5047 |
|   8 |                                      0.737327598 |                      0.372048038 |      0.5046 |
|   9 |                                      0.105332513 |                      0.053147195 |      0.5046 |
|  10 |                                      0.015047502 |                      0.007592318 |      0.5046 |
|  11 |                                      0.002149643 |                      0.001084609 |      0.5046 |
|  12 |                                      0.000307092 |                      0.000154944 |      0.5046 |
|  13 |                                      0.000043870 |                      0.000022135 |      0.5046 |
|  14 |                                      0.000006267 |                      0.000003162 |      0.5046 |
|  15 |                                      0.000000895 |                      0.000000452 |      0.5046 |

\*: Within a given resolution, all pentagons have the same area.

### Average area in m<sup>2</sup>

Here are the same areas, but in m<sup>2</sup>.

| Res | Average <ins>Hexagon</ins> Area (m<sup>2</sup>) | Pentagon Area\* (m<sup>2</sup>) |
| --: | ----------------------------------------------: | ------------------------------: |
|   0 |                           4,357,449,416,078.392 |           2,562,182,162,955.496 |
|   1 |                             609,788,441,794.134 |             328,434,586,246.469 |
|   2 |                              86,801,780,398.997 |              44,930,898,497.879 |
|   3 |                              12,393,434,655.088 |               6,315,472,267.516 |
|   4 |                               1,770,347,654.491 |                 896,582,383.141 |
|   5 |                                 252,903,858.182 |                 127,785,583.023 |
|   6 |                                  36,129,062.164 |                  18,238,749.548 |
|   7 |                                   5,161,293.360 |                   2,604,669.397 |
|   8 |                                     737,327.598 |                     372,048.038 |
|   9 |                                     105,332.513 |                      53,147.195 |
|  10 |                                      15,047.502 |                       7,592.318 |
|  11 |                                       2,149.643 |                       1,084.609 |
|  12 |                                         307.092 |                         154.944 |
|  13 |                                          43.870 |                          22.135 |
|  14 |                                           6.267 |                           3.162 |
|  15 |                                           0.895 |                           0.452 |

\*: Within a given resolution, all pentagons have the same area.

### Hexagon min and max areas

The area of an H3 cell varies based on its position relative to the
[icosahedron vertices](../core-library/overview.md).
We compute the minimum and maximum values for the **hexagon** areas (excluding
the pentagons) at each resolution, and show their ratio.

| Res | Min <ins>Hexagon</ins> Area (km^2) | Max <ins>Hexagon</ins> Area (km^2) | Ratio (max/min) |
| --: | ---------------------------------: | ---------------------------------: | --------------: |
|   0 |                4,106,166.334463915 |                4,977,807.027442012 |        1.212276 |
|   1 |                  447,684.201817940 |                  729,486.875275344 |        1.629468 |
|   2 |                   56,786.622889474 |                  104,599.807218925 |        1.841980 |
|   3 |                    7,725.505769639 |                   14,950.773301379 |        1.935248 |
|   4 |                    1,084.005635363 |                    2,135.986983965 |        1.970457 |
|   5 |                      153.766244448 |                      305.144308779 |        1.984469 |
|   6 |                       21.910021013 |                       43.592111685 |        1.989597 |
|   7 |                        3.126836030 |                        6.227445905 |        1.991613 |
|   8 |                        0.446526174 |                        0.889635157 |        1.992347 |
|   9 |                        0.063780227 |                        0.127090737 |        1.992635 |
|  10 |                        0.009110981 |                        0.018155820 |        1.992740 |
|  11 |                        0.001301542 |                        0.002593689 |        1.992782 |
|  12 |                        0.000185933 |                        0.000370527 |        1.992797 |
|  13 |                        0.000026562 |                        0.000052932 |        1.992802 |
|  14 |                        0.000003795 |                        0.000007562 |        1.992805 |
|  15 |                        0.000000542 |                        0.000001080 |        1.992805 |

## Edge lengths

:::caution
Edge lengths are computed with a **spherical** model of the earth using the
[authalic radius](https://en.wikipedia.org/wiki/Earth_radius#Authalic_radius)
given by
[WGS84](https://en.wikipedia.org/wiki/WGS84)/[EPSG:4326](https://epsg.io/4326).
Average edge lengths were calculated exactly for resolutions 0 through 6 and
extrapolated for finer resolutions.
:::

| Res | Average edge length (Km) |
| --: | -----------------------: |
|   0 |              1281.256011 |
|   1 |              483.0568391 |
|   2 |              182.5129565 |
|   3 |              68.97922179 |
|   4 |              26.07175968 |
|   5 |              9.854090990 |
|   6 |              3.724532667 |
|   7 |              1.406475763 |
|   8 |              0.531414010 |
|   9 |              0.200786148 |
|  10 |              0.075863783 |
|  11 |              0.028663897 |
|  12 |              0.010830188 |
|  13 |              0.004092010 |
|  14 |              0.001546100 |
|  15 |              0.000584169 |

## Appendix: Methodology

<div align="center">
  <img src="/images/pentagon_hexagon_children.png" style={{width:'800px'}} /><br />
  <i>Hexagons have 7 hexagon children. Pentagons have 6 children: 5 hexagons and 1 pentagon.</i>
</div>

### Cell counts

[By definition](../core-library/overview.md), resolution `0` has $110$
**hexagons** and $12$ **pentagons**, for a total of $122$ **cells**.

In fact, _every_ H3 resolution has exactly $12$ **pentagons**, which are always
centered at the icosahedron vertices; the number of **hexagons** increases
with each resolution.

:::tip Formula
Accounting for both **hexagons** and **pentagons**,
the total number of **cells** at resolution $r$ is

$$
c(r) = 2 + 120 \cdot 7^r.
$$

:::

#### Derivation of the cell count formula

We can derive the formula above with the following steps.

First, let $h(n)$ be the number of
children $n \geq 0$ resolution levels below any single **hexagaon**.
Any **hexagon** has $7$ immediate children, so recursion gives us
that

$$
h(n) = 7^n.
$$

Next, let $p(n)$ be the number of children $n \geq 0$ resolution levels below
any single **pentagon**.
Any **pentagon** has $5$ hexagonal immediate children and $1$ pentagonal
immediate child.
Thus, $p(0) = 1$ and $p(1) = 6$.

For $n \geq 1$, we get the general recurrence relation

$$
\begin{aligned}
p(n) &= 5 \cdot  h(n-1) + p(n-1) \\
     &= 5 \cdot 7^{n-1} + p(n-1).
\end{aligned}
$$

For $n \geq 0$, after working through the recurrence, we get that

$$
\begin{aligned}
p(n) &= 1 + 5 \cdot \sum_{k=1}^n\ 7^{k-1} \\
     &= 1 + 5 \cdot \frac{7^n - 1}{6},
\end{aligned}
$$

using the closed form for a
[geometric series](https://en.wikipedia.org/wiki/Geometric_series).

Finally, using the closed forms for $h(n)$ and $p(n)$,
and the fact that ([by definition](../core-library/overview.md))
resolution `0` has
$12$ **pentagons** and $110$ **hexagons**,
we get the closed form for the total number of **cells**
at resolution $r$ as

$$
\begin{aligned}
c(r) &= 12 \cdot p(r) + 110 \cdot h(r) \\
     &= 2 + 120 \cdot 7^r.
\end{aligned}
$$

#### Jupyter notebook

A notebook to produce the cell count table above can be
[found here](https://github.com/uber/h3-py-notebooks/blob/master/notebooks/stats_tables/cell_counts.ipynb).

### Cell areas

Cell areas are computed with a **spherical** model of the earth using the
[authalic radius](https://en.wikipedia.org/wiki/Earth_radius#Authalic_radius)
given by
[WGS84](https://en.wikipedia.org/wiki/WGS84)/[EPSG:4326](https://epsg.io/4326).

The [`h3-py-notebooks` repo](https://github.com/uber/h3-py-notebooks)
has notebooks for producing the
[average cell area table](https://github.com/uber/h3-py-notebooks/blob/master/notebooks/stats_tables/avg_area_table.ipynb)
and the
[min/max area table](https://github.com/uber/h3-py-notebooks/blob/master/notebooks/stats_tables/extreme_hex_area.ipynb).

# === library/terminology ===

---

id: terminology
title: Terminology
sidebar_label: Terminology
slug: /library/terminology

---

The following are technical terms used by H3.

- `H3Index`:
  - an unsigned 64-bit integer representing _any_ H3 object (hexagon, pentagon, directed edge ...)
  - often represented as a 15-character (or 16-character) hexadecimal string, like `'8928308280fffff'`
  - the full term "H3 index" should be used to avoid confusion with other common uses of "index";
    when a "traditional" index is needed, prefer using "number", "pos", or another term to avoid confusion
- **mode**:
  - an integer describing the type of object being represented by an H3 index
  - this integer is encoded in the `H3Index`
- **cell** or **H3 cell**:
  - a geometric/geographic unit polygon in the H3 grid, corresponding to an `H3Index` of `mode 1` (hexagon or pentagon)
  - for functions that can handle either hexagons or pentagons, the more general term "cell" should be used whenever possible
- **hexagon**:
  - an H3 **cell** that is a **topological** hexagon
  - below, we explain that functions that _only_ work with **hexagons** have an `Unsafe` suffix;
    these functions are paired with ones having a `Safe` suffix, meaning they can handle **pentagons**, but are slower
- **pentagon**:
  - an H3 **cell** that is a **topological** pentagon
- **directed edge**:
  - represents a traversal from an origin **cell** to an adjacent destination **cell**
  - corresponds to an `H3Index` of `mode 2`
- **grid**:
  - the graph with nodes corresponding to H3 cells, and edges given by pairs of adjacent cells
  - for example, `gridDistance` is the minimal number of edges in a graph path connecting two cells
- **lat/lng point**:
  - a representation of a geographic point in terms of a latitude/longitude pair
  - when abbreviating, we use "lng" (instead of "lon") for longitude
- **topological**:
  - H3 cells are **topological** pentagons or hexagons, in the sense that they have 5 or 6 neighbors, respectively, in the H3 **grid**
  - the majority of **hexagons** are also **geometric** hexagons (similarly with **pentagons**), in that they have 6 edges and vertices when represented as polygons of lat/lng points
  - a small number of **hexagons** are not **geometric** hexagons (similarly with **pentagons**), in that they have extra vertices and edges due to distortion around icosahedron boundaries
  - for more details, see this [h3-js issue](https://github.com/uber/h3-js/issues/53) or this [Observable post](https://observablehq.com/@fil/h3-oddities)
- **base cell**:
  - one of the 122 H3 **cells** (110 hexagons and 12 pentagons) of resolution `0`
  - every other cell in H3 is a child of a base cell
  - each base cell has a "base cell number" (0--121), which is encoded into the `H3Index` representation of every H3 cell
  - there is a one-to-one correspondence between the "base cell number" and the `H3Index` representation of resolution `0` cells
    - e.g., base cell 0 has `H3Index` hexadecimal representation `'8001fffffffffff'`
- **boundary**:
  - all or part of the list of geometric points that enclose an H3 cell
  - may include more than 6 points in the case that a cell is not a geometric hexagon, such as when a hexagon crosses an icosahedron boundary
  - may also be used to describe the boundary between two geometric cells, as in the case of an edge
  - represented in the H3 codebase with the `CellBoundary` struct (previously `GeoBoundary` before v4.0)
- `H3_NULL`:
  - equivalent to `0` and guaranteed to never be a valid `H3Index` (even after any future H3 **modes** are added)
  - returned by functions to denote an error, or to denote missing data in arrays of `H3Index`
  - analogous to `NaN` in floating point

### Use of "hex", "hexagon", "cell", "pentagon", etc.

We realize that "hex" or "hexagon" will still be used informally to refer to the concept of "cell" (As the development team, we do it ourselves!).
This should be expected in casual, informal discussions of H3.
However, when _precision_ is required, we advise the use of strict technical terms like "index", "cell", "hexagon", "pentagon", etc.
In the codebase and in the documentation, strictly correct terminology should _always_ be used, as many functions and algorithms distinguish between hexagons and pentagons.

## References

- [Technical RFC for naming concepts](https://github.com/uber/h3/blob/master/dev-docs/RFCs/v4.0.0/names_for_concepts_types_functions.md)

# === observable-notebooks ===

Here are all 62 of Nick Rabinowitz's public Observable notebooks with their API-style links:

### H3 Tutorials

```
https://api.observablehq.com/@nrabinowitz/h3-tutorial-the-h3-js-library.js
  # H3 Tutorial: Intro to h3-js (v3) — Intro to the h3-js v3 API: indexing, hierarchy, traversal, regions

https://api.observablehq.com/@nrabinowitz/h3-tutorial-intro-to-h3-js-v4.js
  # H3 Tutorial: Intro to h3-js (v4) — Same intro updated for h3-js v4 function names

https://api.observablehq.com/@nrabinowitz/h3-tutorial-heatmap-rendering.js
  # H3 Tutorial: Rendering Hexagons — Rendering H3 heatmaps on a MapboxGL map

https://api.observablehq.com/@nrabinowitz/h3-tutorial-using-point-layers.js
  # H3 Tutorial: Using Point Layers — Converting point data to H3 with buffering operations

https://api.observablehq.com/@nrabinowitz/h3-tutorial-using-polygon-layers.js
  # H3 Tutorial: Using Polygon Layers — Converting polygon layers (census tracts) to H3 hexagons

https://api.observablehq.com/@nrabinowitz/h3-tutorial-suitability-analysis.js
  # H3 Tutorial: Suitability Analysis — Combining weighted H3 layers to find optimal locations

https://api.observablehq.com/@nrabinowitz/h3-radius-lookup.js
  # H3 Radius Lookup — Efficient radius search using k-rings vs. Haversine distance
```

### H3 Core / Visualization

```
https://api.observablehq.com/@nrabinowitz/h3-index-inspector.js
  # H3 Index Inspector — Interactive tool to inspect and explore H3 index properties

https://api.observablehq.com/@nrabinowitz/h3-index-bit-layout.js
  # H3 Index Bit Layout — Visualizing the binary structure of H3 index encoding

https://api.observablehq.com/@nrabinowitz/h3-area-variation.js
  # H3: Area Variation — Visualizing how hexagon area varies across the globe

https://api.observablehq.com/@nrabinowitz/h3-area-stats.js
  # H3: Area/Edge Length Stats — Statistics on area and edge length across resolutions

https://api.observablehq.com/@nrabinowitz/h3-indexing-order.js
  # H3: Indexing Order — Visualizing the ordering of H3 indexes

https://api.observablehq.com/@nrabinowitz/h3-direction-reference.js
  # H3 Direction Reference — Reference for H3 grid directions

https://api.observablehq.com/@nrabinowitz/h3-vertex-mode.js
  # H3: Vertex Mode — Exploring H3 vertex mode functionality

https://api.observablehq.com/@nrabinowitz/h3-indexes-cartesian-vs-spherical.js
  # H3 Indexes: Cartesian vs Spherical — Comparing Cartesian and spherical coordinate approaches

https://api.observablehq.com/@nrabinowitz/h3-iterate-over-all-indexes.js
  # H3: Iterate Over All Indexes — Iterating over all H3 indexes at a given resolution

https://api.observablehq.com/@nrabinowitz/h3-hierarchical-non-containment.js
  # H3 Hierarchical (Non)Containment — Demonstrating imperfect parent-child containment

https://api.observablehq.com/@nrabinowitz/h3-celltochildpos.js
  # H3: cellToChildPos and childPosToCell — Exploring child position functions in H3

https://api.observablehq.com/@nrabinowitz/h3-convex-hull.js
  # H3 Convex Hull — Computing convex hulls of H3 cell sets

https://api.observablehq.com/@nrabinowitz/h3-centroid.js
  # H3 Centroid — Computing centroids of H3 cell sets

https://api.observablehq.com/@nrabinowitz/h3-line-algo-comparison.js
  # H3: Line Comparisons — Comparing H3 line algorithms

https://api.observablehq.com/@nrabinowitz/h3-polar-issues-with-polgon-to-cells.js
  # H3: Polar Issues with Polygon to Cells — Investigating polar region edge cases

https://api.observablehq.com/@nrabinowitz/h3-polyfill-modes.js
  # H3 Polyfill Modes — Comparing different polyfill/polygon-to-cells modes

https://api.observablehq.com/@nrabinowitz/h3-multipolygon-issue.js
  # H3 MultiPolygon Issue — Debugging multipolygon conversion issues
```

### H3 Applications

```
https://api.observablehq.com/@nrabinowitz/h3-travel-times.js
  # H3 Travel Times — Visualizing travel time data with H3

https://api.observablehq.com/@nrabinowitz/h3-pathfinding.js
  # H3 Pathfinding — Pathfinding algorithms on the H3 grid

https://api.observablehq.com/@nrabinowitz/h3-adaptive-grid.js
  # H3 Adaptive Grid — Multi-resolution adaptive grids with H3

https://api.observablehq.com/@nrabinowitz/h3-cell-counts-per-country.js
  # Cell counts per country — Counting H3 cells within country boundaries

https://api.observablehq.com/@nrabinowitz/indexing-polygons-with-h3.js
  # Indexing Polygons With H3 — Techniques for indexing polygon geometries

https://api.observablehq.com/@nrabinowitz/privacy-preserving-spatial-indexing-with-h3.js
  # Privacy-Preserving Spatial Indexing with H3 — Using H3 for privacy-aware geospatial data

https://api.observablehq.com/@nrabinowitz/surface-construction-with-h3.js
  # Surface construction with H3 — Building 3D surfaces from H3 data

https://api.observablehq.com/@nrabinowitz/shape-simplification-with-h3.js
  # Shape simplification with H3 — Simplifying geographic shapes using H3

https://api.observablehq.com/@nrabinowitz/h3-continuous-elevation.js
  # H3 Continuous Elevation — Continuous elevation rendering with H3

https://api.observablehq.com/@nrabinowitz/h3-elevation.js
  # H3 Elevation — 3D elevation visualization with H3

https://api.observablehq.com/@nrabinowitz/spidering-polyfill.js
  # Spidering polyfill — Spidering approach to polygon fill with H3

https://api.observablehq.com/@nrabinowitz/flat-h3-grid-via-gnomonic-projection.js
  # "Flat" H3 Grid via Gnomonic Projection — Rendering H3 on a flat plane via projection

https://api.observablehq.com/@nrabinowitz/h3-game-of-life.js
  # H3: Game of Life — Conway's Game of Life on the H3 hexagonal grid

https://api.observablehq.com/@nrabinowitz/h3-index-notebook-template.js
  # H3 Index Notebook: Template — Starter template for H3 Observable notebooks
```

### H3 Map Rendering

```
https://api.observablehq.com/@nrabinowitz/h3-mapbox-style-heat-map.js
  # H3 Mapbox Style Heat Map — Heatmap rendering using Mapbox styling

https://api.observablehq.com/@nrabinowitz/h3-mapbox-style-cluster-map.js
  # H3 Mapbox Style Cluster Map — Cluster map rendering using Mapbox styling

https://api.observablehq.com/@nrabinowitz/h3-deck-gl-heat-map.js
  # H3 Deck.gl Heat Map — Heatmap rendering using deck.gl

https://api.observablehq.com/@nrabinowitz/untitled.js
  # H3 Clusters: Conversion to coarser resolution perf comparison — Performance comparison for resolution conversion
```

### Non-H3 Notebooks

```
https://api.observablehq.com/@nrabinowitz/comparison-of-tile-standard-deviation.js
  # Comparison of standard deviation from center in different tile shapes

https://api.observablehq.com/@nrabinowitz/exercise.js
  # Exercise — Personal exercise tracking

https://api.observablehq.com/@nrabinowitz/polygon-simplification.js
  # Polygon Simplification — General polygon simplification techniques

```

### Utility Notebooks (imported by other notebooks)

```
https://api.observablehq.com/@nrabinowitz/mapbox-utils.js
  # Mapbox Utils — Shared MapboxGL utility functions

https://api.observablehq.com/@nrabinowitz/mapbox-token.js
  # Mapbox Token — Shared Mapbox API token for map notebooks
```

Each URL follows the pattern `https://api.observablehq.com/@nrabinowitz/{slug}.js` and returns the full notebook source as a JavaScript module.

# === quickstart ===

---

id: quickstart
title: Quick Start
sidebar_label: Quick Start
slug: /quickstart

---

This page shows you how to get started with the functions in H3 that convert points to cell identifiers, and from cell identifiers back to geometry. These are the core indexing functions used in many applications of H3.

You can run the code on this page directly in your browser. The page uses the JavaScript bindings for H3 to run the code, or follow along with the same API in [your preferred programming language](/docs/community/bindings).

## Point / cell

First, we'll take the coordinates of the Ferry Building in San Francisco and find the containing H3 cell:

```js live
function example() {
  const lat = 37.7955;
  const lng = -122.3937;
  const res = 10;
  return h3.latLngToCell(lat, lng, res);
}
```

The result is the identifier of the hexagonal cell in H3 containing this point. We can retrieve the center of this cell:

```js live
function example() {
  const h = "8a283082a677fff";
  return h3.cellToLatLng(h);
}
```

Note that the result of this example is not our original coordinates. That's because the identifier represents the hexagonal cell, not the coordinates. All points indexed in H3 within the bounds of this cell will have the same identifier. We can find the bounds of this cell:

```js live
function example() {
  const h = "8a283082a677fff";
  return h3.cellToBoundary(h);
}
```

# === tutorials ===

> **Version Note**: Tutorial 1 (v4 Intro) and Tutorial 6 (Radius Lookup) use h3-js v4 API names.
> Tutorials 2-5 were written for h3-js v3 and use deprecated function names
> (e.g., `geoToH3` instead of `latLngToCell`, `kRing` instead of `gridDisk`).
> When generating code, always use v4 function names from SKILL.md.

# H3 Tutorial: Intro to h3-js (v4)

![H3 Grid](https://gist.githubusercontent.com/nrabinowitz/d3a5ca3e3e40727595dd137b65058c76/raw/9758ff41bb283608b33d3b864a5a576d70e8229e/grid_tan.png)
The h3-js library is a JavaScript version of [H3](https://uber.github.io/h3), Uber's hexagon-based geospatial indexing system. The code is transpiled from C using [emscripten](https://emscripten.org/). This intro provides a quick overview of common functions in h3-js v4, which changed most function names in the API.
[github.com/uber/h3-js](https://github.com/uber/h3-js)

## Core Functions

The core of the h3-js library are the functions that provide the H3 index for geographic coordinates and vice versa. Finding an H3 index requires the caller to specify the grid resolution, which determines the size of the hexagon. The higher the resolution of the grid, the smaller the hexagons, from res 0 (continental) to res 15 (1 square meter). Res 9 is roughly a city block.

```js
// Index a lat/lng point to an H3 index
h3.latLngToCell(20, 123, 2);
```

```js
// Get the center of an H3 index as a lat/lng point
h3.cellToLatLng("8928342e20fffff");
```

```js
// Get the vertices of an H3 index as lat/lng points.
// Passing "true" as the second parameter yields GeoJSON lng/lat points and a closed loop.
h3.cellToBoundary("8928342e20fffff", true);
```

## Hierarchy

The H3 grid has a hierarchical relationship between resolutions. Each hexagon has 7 children at the next resolution, although the areas of these children are not perfectly contained in the parent. h3-js provides functions to move up and down this hierachy.

```js
// Get the children of an H3 index at the given (finer) resolution
h3.cellToChildren("8928342e20fffff", 10);
```

```js
// Get the parent of an H3 index at the given (coarser) resolution
h3.cellToParent("8928342e20fffff", 7);
```

## Traversal

A hexagon-based grid lends itself well to traversal, as each cell has 6 unambiguous neighbors (or 5, for the 12 pentagons at each resolution). h3-js provides functions to traverse neighbors by distance from some origin index.

```js
// Find all H3 indexes within a given distance from the origin (filled ring)
h3.gridDisk("8728342e2ffffff", 1);
```

```js
// Find all H3 indexes within a given distance from the origin, grouped into hollow rings
// from innermost to outermost
h3.gridDiskDistances("8728342e2ffffff", 3);
```

```js
// Get the distance in grid cells between two H3 indexes
h3.gridDistance("85283473fffffff", "8528362bfffffff");
```

```js
// Get a path of cells between two H3 indexes
h3.gridPathCells("85283473fffffff", "8528362bfffffff");
```

## Regions

The h3-js library also provides conversion functions between polygons and sets of H3 indexes, allowing users to work with arbitrarily-shaped geographic regions.

```js
// Get all H3 indexes within a geographic polygon. Inclusion is determined by whether the center
// of a given cell falls within the polygon.
h3.polygonToCells(
  [
    [
      [37, -122],
      [36, -121],
      [36, -123],
    ],
  ],
  5,
);
```

```js
// Get the multipolygon (array of polygons) for a set of H3 indexes. Indexes are expected to
// be unique and all at the same resolution
h3.cellsToMultiPolygon([
  "85291a6ffffffff",
  "85291a6bfffffff",
  "852834d3fffffff",
]);
```

## And More!

The H3 library provides a range of other functions, including utilities for inspecting H3 indexes, indexing edges between cells, and getting metadata about the grid. You can see the full API documentation on GitHub: [github.com/uber/h3-js](https://github.com/uber/h3-js)

## Dependencies

```js
h3 = require("h3-js@4.0.1");
```

---

## H3 Tutorial: Intro to h3-js (v3)

````markdown
# H3 Tutorial: Intro to h3-js (v3)

![H3 Grid](https://gist.githubusercontent.com/nrabinowitz/d3a5ca3e3e40727595dd137b65058c76/raw/9758ff41bb283608b33d3b864a5a576d70e8229e/grid_tan.png)

The h3-js library is a JavaScript version of [H3](https://uber.github.io/h3), Uber's hexagon-based geospatial indexing system. **Note:** This page covers h3-js v3. For v4, see the [h3-js v4 tutorial](https://observablehq.com/@nrabinowitz/h3-tutorial-intro-to-h3-js-v4).

[github.com/uber/h3-js](https://github.com/uber/h3-js)

## Core Functions

The core of the h3-js library are the functions that provide the H3 index for geographic coordinates and vice versa. Finding an H3 index requires the caller to specify the grid resolution, which determines the size of the hexagon. The higher the resolution of the grid, the smaller the hexagons, from res 0 (continental) to res 15 (1 square meter). Res 9 is roughly a city block.

```js
// Index a lat/lng point to an H3 index
h3.geoToH3(20, 123, 2);
```

```js
// Get the center of an H3 index as a lat/lng point
h3.h3ToGeo("8928342e20fffff");
```

```js
// Get the vertices of an H3 index as lat/lng points
h3.h3ToGeoBoundary("8928342e20fffff");
```

## Hierarchy

The H3 grid has a hierarchical relationship between resolutions. Each hexagon has 7 children at the next resolution, although the areas of these children are not perfectly contained in the parent. h3-js provides functions to move up and down this hierachy.

```js
// Get the children of an H3 index at the given (finer) resolution
h3.h3ToChildren("8928342e20fffff", 10);
```

```js
// Get the parent of an H3 index at the given (coarser) resolution
h3.h3ToParent("8928342e20fffff", 7);
```

## Traversal

A hexagon-based grid lends itself well to traversal, as each cell has 6 unambiguous neighbors (or 5, for the 12 pentagons at each resolution). h3-js provides functions to traverse neighbors by distance from some origin index.

```js
// Find all H3 indexes within a given distance from the origin (filled ring)
h3.kRing("8728342e2ffffff", 1);
```

```js
// Find all H3 indexes a specific distance from the origin (hollow ring)
h3.hexRing("8728342e2ffffff", 1);
```

```js
// Get the distance in grid cells between two H3 indexes
h3.h3Distance("8728342e6ffffff", "8728342c4ffffff");
```

## Regions

The h3-js library also provides conversion functions between polygons and sets of H3 indexes, allowing users to work with arbitrarily-shaped geographic regions.

```js
// Get all H3 indexes within a geographic polygon
h3.polyfill(
  [
    [
      [37, -122],
      [36, -121],
      [36, -123],
    ],
  ],
  5,
);
```

```js
// Get the multipolygon (array of polygons) for a set of H3 indexes
h3.h3SetToMultiPolygon([
  "85291a6ffffffff",
  "85291a6bfffffff",
  "852834d3fffffff",
]);
```

## And More!

The H3 library provides a range of other functions, including utilities for inspecting H3 indexes, indexing edges between cells, and getting metadata about the grid. You can see the full API documentation on GitHub: [github.com/uber/h3-js](https://github.com/uber/h3-js)

## Dependencies

```js
h3 = require("h3-js@3.7.2");
```
````

---

## 2. H3 Tutorial: Rendering Hexagons

````markdown
# H3 Tutorial: Rendering Hexagons

There are a variety of different ways to render H3 hexagons on a map. This tutorial demonstrates a simple approach to rendering an H3 heatmap using MapboxGL.

## Data

Create dummy data as a map of h3 indexes to values between 0 and 1. There are lots of other data formats that could work here, but a map makes it easy to associate a hexagon with a value.

```js
const hexagons = (() => {
  const centerHex = h3.geoToH3(config.lat, config.lng, 8);
  const kRing = h3.kRing(centerHex, 3);
  // Reduce hexagon list to a map with random values
  return kRing.reduce(
    (res, hexagon) => ({ ...res, [hexagon]: Math.random() }),
    {},
  );
})();
```

## Map Rendering

Using MapboxGL, create an interactive map to show our data as a hexagon heatmap layer. The map will update appropriately when the data changes.

```js
function* map(
  mapboxgl,
  mapContainer,
  config,
  renderHexes,
  hexagons,
  renderAreas,
) {
  let map = this;
  if (!map) {
    map = new mapboxgl.Map({
      container: mapContainer,
      center: [config.lng, config.lat],
      zoom: config.zoom,
      style: "mapbox://styles/mapbox/light-v9",
    });
  }

  // Wait until the map loads, then yield the container again.
  yield new Promise((resolve) => {
    if (map.loaded()) resolve(map);
    else map.on("load", () => resolve(map));
  });

  renderHexes(map, hexagons);
  renderAreas(map, hexagons, 0.75);
}
```

The `renderHexes` function adds the geojson data source and associated layer to the map, updating when data or configuration changes.

```js
function renderHexes(map, hexagons) {
  // Transform the current hexagon map into a GeoJSON object
  const geojson = geojson2h3.h3SetToFeatureCollection(
    Object.keys(hexagons),
    (hex) => ({ value: hexagons[hex] }),
  );

  const sourceId = "h3-hexes";
  const layerId = `${sourceId}-layer`;
  let source = map.getSource(sourceId);

  // Add the source and layer if we haven't created them yet
  if (!source) {
    map.addSource(sourceId, {
      type: "geojson",
      data: geojson,
    });
    map.addLayer({
      id: layerId,
      source: sourceId,
      type: "fill",
      interactive: false,
      paint: {
        "fill-outline-color": "rgba(0,0,0,0)",
      },
    });
    source = map.getSource(sourceId);
  }

  // Update the geojson data
  source.setData(geojson);

  // Update the layer paint properties, using the current config values
  map.setPaintProperty(layerId, "fill-color", {
    property: "value",
    stops: [
      [0, config.colorScale[0]],
      [0.5, config.colorScale[1]],
      [1, config.colorScale[2]],
    ],
  });
  map.setPaintProperty(layerId, "fill-opacity", config.fillOpacity);
}
```

If we only care about values above a certain threshold, we might want to simply render those areas of the map as outlines, instead of rendering the whole heatmap. This allows us to focus on regions of interest, without obscuring the map behind the hex layer. The `renderAreas` function filters by threshold and renders the resulting outline.

```js
function renderAreas(map, hexagons, threshold) {
  // Transform the current hexagon map into a GeoJSON object
  const geojson = geojson2h3.h3SetToFeature(
    Object.keys(hexagons).filter((hex) => hexagons[hex] > threshold),
  );

  const sourceId = "h3-hex-areas";
  const layerId = `${sourceId}-layer`;
  let source = map.getSource(sourceId);

  // Add the source and layer if we haven't created them yet
  if (!source) {
    map.addSource(sourceId, {
      type: "geojson",
      data: geojson,
    });
    map.addLayer({
      id: layerId,
      source: sourceId,
      type: "line",
      interactive: false,
      paint: {
        "line-width": 3,
        "line-color": config.colorScale[2],
      },
    });
    source = map.getSource(sourceId);
  }

  // Update the geojson data
  source.setData(geojson);
}
```

## Configuration

```js
const config = {
  lng: -122.4,
  lat: 37.7923539,
  zoom: 11.5,
  fillOpacity: 0.6,
  colorScale: ["#ffffcc", "#78c679", "#006837"],
};
```

## Dependencies

- [MapboxGL](https://www.mapbox.com/mapbox-gl-js/api/) is our map-rendering library
- [h3-js](https://github.com/uber/h3-js) provides the core logic and algorithms for the hexagon grid system
- [geojson2h3](https://github.com/uber/geojson2h3) includes utilities for converting between H3 and GeoJSON

```js
mapboxgl = require("mapbox-gl@0.43.0");
h3 = require("h3-js@3.7.2");
geojson2h3 = require("https://bundle.run/geojson2h3@1.0.1");
```
````

---

## 3. H3 Tutorial: Using Point Layers

````markdown
# H3 Tutorial: Using Point Layers

Converting a point layer to H3 is quite straightforward, as binning into hexagon cells is H3's core functionality. This tutorial demonstrates how to extend basic binning with buffering operations.

## Data

Here we're loading BART station locations in GeoJSON format. Source: [bart.gov](https://www.bart.gov/schedules/developers/geo)

```js
const bartStations = await d3Fetch.json(
  "https://gist.githubusercontent.com/nrabinowitz/d3a5ca3e3e40727595dd137b65058c76/raw/8f1a3e30113472404feebc288e83688a6d5cf33d/bart.json",
);
```

We have several options for transforming the point layer to H3 indexes with associated values. The simplest is just to count the number of stations in each hexagon.

```js
function countPoints(geojson) {
  const layer = {};
  geojson.features.forEach((feature) => {
    const [lng, lat] = feature.geometry.coordinates;
    const h3Index = h3.geoToH3(lat, lng, h3Resolution);
    layer[h3Index] = (layer[h3Index] || 0) + 1;
  });
  return normalizeLayer(layer, true);
}
```

If we're using a relatively fine resolution, however, this gives us a lot of individual hexagons. If we're interested in e.g. "areas within walking distance of a BART station", we need to buffer.

```js
function bufferPoints(geojson, radius) {
  const layer = {};
  geojson.features.forEach((feature) => {
    const [lng, lat] = feature.geometry.coordinates;
    const stationIndex = h3.geoToH3(lat, lng, h3Resolution);
    const ring = h3.kRing(stationIndex, radius);
    ring.forEach((h3Index) => {
      layer[h3Index] = (layer[h3Index] || 0) + 1;
    });
  });
  return normalizeLayer(layer, true);
}
```

It's often useful to have the "influence" of a given point degrade with distance. H3 makes it relatively simple to assign different values to each concentric ring.

```js
function bufferPointsLinear(geojson, radius) {
  const layer = {};
  geojson.features.forEach((feature) => {
    const [lng, lat] = feature.geometry.coordinates;
    const stationIndex = h3.geoToH3(lat, lng, h3Resolution);
    // add surrounding multiple surrounding rings, with less weight in each
    const rings = h3.kRingDistances(stationIndex, radius);
    const step = 1 / (radius + 1);
    rings.forEach((ring, distance) => {
      ring.forEach((h3Index) => {
        layer[h3Index] = (layer[h3Index] || 0) + 1 - distance * step;
      });
    });
  });
  return normalizeLayer(layer);
}
```

## Utilities

```js
function normalizeLayer(layer, zeroBaseline = false) {
  const hexagons = Object.keys(layer);
  // Pass one, get max (and min if needed)
  const max = hexagons.reduce(
    (max, hex) => Math.max(max, layer[hex]),
    -Infinity,
  );
  const min = zeroBaseline
    ? 0
    : hexagons.reduce((min, hex) => Math.min(min, layer[hex]), Infinity);
  // Pass two, normalize
  hexagons.forEach((hex) => {
    layer[hex] = (layer[hex] - min) / (max - min);
  });
  return layer;
}
```

```js
function kmToRadius(km) {
  return Math.floor(km / h3.edgeLength(h3Resolution, h3.UNITS.km));
}
```

## Map Rendering

```js
function* map(mapboxgl, mapContainer, config, renderHexes, hexagons) {
  let map = this;
  if (!map) {
    map = new mapboxgl.Map({
      container: mapContainer,
      center: [config.lng, config.lat],
      zoom: config.zoom,
      style: "mapbox://styles/mapbox/light-v9",
    });
  }

  yield new Promise((resolve) => {
    if (map.loaded()) resolve(map);
    else map.on("load", () => resolve(map));
  });

  renderHexes(map, hexagons);
}
```

```js
function renderHexes(map, hexagons) {
  const geojson = geojson2h3.h3SetToFeatureCollection(
    Object.keys(hexagons),
    (hex) => ({ value: hexagons[hex] }),
  );

  const sourceId = "h3-hexes";
  const layerId = `${sourceId}-layer`;
  let source = map.getSource(sourceId);

  if (!source) {
    map.addSource(sourceId, {
      type: "geojson",
      data: geojson,
    });
    map.addLayer({
      id: layerId,
      source: sourceId,
      type: "fill",
      interactive: false,
      paint: {
        "fill-outline-color": "rgba(0,0,0,0)",
      },
    });
    source = map.getSource(sourceId);
  }

  source.setData(geojson);

  map.setPaintProperty(layerId, "fill-color", {
    property: "value",
    stops: [
      [0, config.colorScale[0]],
      [0.5, config.colorScale[1]],
      [1, config.colorScale[2]],
    ],
  });
  map.setPaintProperty(layerId, "fill-opacity", config.fillOpacity);
}
```

## Config

```js
const config = {
  lng: -122.2,
  lat: 37.7923539,
  zoom: 10.5,
  fillOpacity: 0.75,
  colorScale: ["#ffffD9", "#50BAC3", "#1A468A"],
};
```

## Dependencies

```js
d3Fetch = require("d3-fetch");
mapboxgl = require("mapbox-gl@0.43.0");
h3 = require("https://bundle.run/h3-js@3.1.0");
geojson2h3 = require("https://bundle.run/geojson2h3@1.0.1");
```
````

---

## 4. H3 Tutorial: Using Polygon Layers

````markdown
# H3 Tutorial: Using Polygon Layers

Many geographic data sets encode their data in polygonal regions. This tutorial demonstrates how to convert polygon layers to sets of H3 hexagons.

## Data

Here we're loading raw data in GeoJSON format. Each element of the data is a polygon representing an Oakland census tract, with a value showing mean travel times (in seconds) from downtown San Francisco. Source: [movement.uber.com](https://movement.uber.com/explore/san_francisco/travel-times)

```js
const sfTravelTimes = await d3Fetch.json(
  "https://gist.githubusercontent.com/nrabinowitz/d3a5ca3e3e40727595dd137b65058c76/raw/657a9f3b64fedc718c3882cd4adc645ac0b4cfc5/oakland_travel_times.json",
);
```

Transforming the polygons to hexagons is relatively straightforward using `geojson2h3`. As we know in this case that the polygons don't overlap, each hexagon simply takes the value of the polygon that contains its center.

```js
const hexagons = (() => {
  const layer = {};
  sfTravelTimes.features.forEach((feature) => {
    const hexagons = geojson2h3.featureToH3Set(feature, h3Resolution);
    hexagons.forEach((h3Index) => {
      layer[h3Index] = feature.properties.travelTime;
    });
  });
  return normalizeLayer(layer);
})();
```

As we've defined our rendering utilities to expect a value between 0 and one, we set up a `normalizeLayer` utility to normalize all the hexagon values to this range.

```js
function normalizeLayer(layer, zeroBaseline = false) {
  const hexagons = Object.keys(layer);
  const max = hexagons.reduce(
    (max, hex) => Math.max(max, layer[hex]),
    -Infinity,
  );
  const min = zeroBaseline
    ? 0
    : hexagons.reduce((min, hex) => Math.min(min, layer[hex]), Infinity);
  hexagons.forEach((hex) => {
    layer[hex] = (layer[hex] - min) / (max - min);
  });
  return layer;
}
```

## Map Rendering

```js
function* map(mapboxgl, mapContainer, config, renderHexes, hexagons) {
  let map = this;
  if (!map) {
    map = new mapboxgl.Map({
      container: mapContainer,
      center: [config.lng, config.lat],
      zoom: config.zoom,
      style: "mapbox://styles/mapbox/light-v9",
    });
  }

  yield new Promise((resolve) => {
    if (map.loaded()) resolve(map);
    else map.on("load", () => resolve(map));
  });

  renderHexes(map, hexagons);
}
```

```js
function renderHexes(map, hexagons) {
  const geojson = geojson2h3.h3SetToFeatureCollection(
    Object.keys(hexagons),
    (hex) => ({ value: hexagons[hex] }),
  );

  const sourceId = "h3-hexes";
  const layerId = `${sourceId}-layer`;
  let source = map.getSource(sourceId);

  if (!source) {
    map.addSource(sourceId, {
      type: "geojson",
      data: geojson,
    });
    map.addLayer({
      id: layerId,
      source: sourceId,
      type: "fill",
      interactive: false,
      paint: {
        "fill-outline-color": "rgba(0,0,0,0)",
      },
    });
    source = map.getSource(sourceId);
  }

  source.setData(geojson);

  map.setPaintProperty(layerId, "fill-color", {
    property: "value",
    stops: [
      [0, config.colorScale[0]],
      [0.5, config.colorScale[1]],
      [1, config.colorScale[2]],
    ],
  });
  map.setPaintProperty(layerId, "fill-opacity", config.fillOpacity);
}
```

## Config

```js
const config = {
  lng: -122.2,
  lat: 37.7923539,
  zoom: 10.5,
  fillOpacity: 0.75,
  colorScale: ["#ffffD9", "#50BAC3", "#1A468A"],
};
```

## Dependencies

```js
d3Fetch = require("d3-fetch");
mapboxgl = require("mapbox-gl@0.43.0");
h3 = require("https://bundle.run/h3-js@3.1.0");
geojson2h3 = require("https://bundle.run/geojson2h3@1.0.1");
```
````

---

## 5. H3 Tutorial: Suitability Analysis

````markdown
# H3 Tutorial: Suitability Analysis

Suitability analysis is an approach used in the GIS field to identify optimal geographic locations for some specific use - for example, the best place to locate a new store or transit station. While the process is fairly straightforward - different geographic layers are added together with subjectively defined weights to produce a composite layer - combining arbitrary layers can be challenging. H3 simplifies this problem by providing hexagon grid cells as a common, uniform unit of analysis.

## Data Layers

We'll take each of the raw data layers we're bringing in and convert them to hexagon layers. Each layer will be a map of H3 index to some value normalized between zero and 1.

```js
// Crime layer - Oakland crime reports, last 90 days
const crimeLayer = (() => {
  const layer = {};
  crime90days.forEach(({ lat, lng }) => {
    const h3Index = h3.geoToH3(lat, lng, h3Resolution);
    layer[h3Index] = (layer[h3Index] || 0) + 1;
  });
  return normalizeLayer(layer);
})();
```

```js
// Schools layer - Oakland public school locations
const schoolsLayer = (() => {
  const layer = {};
  publicSchools.forEach(({ lat, lng }) => {
    const h3Index = h3.geoToH3(lat, lng, h3Resolution);
    // Add school hex
    layer[h3Index] = (layer[h3Index] || 0) + 1;
    // add surrounding kRing, with less weight
    h3.hexRing(h3Index, 1).forEach((neighbor) => {
      layer[neighbor] = (layer[neighbor] || 0) + 0.5;
    });
  });
  return normalizeLayer(layer);
})();
```

```js
// BART layer - using buffered point layer with linear falloff
const bartLayer = normalizeLayer(
  bufferPointsLinear(bartStations, kmToRadius(1)),
);
```

```js
// Travel time layer - lower travel time is better, so we take the inverse
const travelTimeLayer = (() => {
  const layer = {};
  sfTravelTimes.features.forEach((feature) => {
    const hexagons = geojson2h3.featureToH3Set(feature, h3Resolution);
    hexagons.forEach((h3Index) => {
      // Lower is better, so take the inverse
      layer[h3Index] =
        (layer[h3Index] || 0) + 1 / feature.properties.travelTime;
    });
  });
  return normalizeLayer(layer, true);
})();
```

```js
// Cafes layer - Oakland points of interest filtered to food/drink
const cafesLayer = (() => {
  const layer = {};
  pois
    .filter(
      (poi) =>
        poi.type === "Cafes" ||
        poi.type === "Places to Eat" ||
        poi.type === "Restaurant",
    )
    .forEach(({ lat, lng }) => {
      const h3Index = h3.geoToH3(lat, lng, h3Resolution);
      layer[h3Index] = (layer[h3Index] || 0) + 1;
    });
  return normalizeLayer(layer);
})();
```

## Combining Layers

```js
const mapLayers = [
  { hexagons: schoolsLayer, weight: schoolWeight },
  { hexagons: bartLayer, weight: bartWeight },
  { hexagons: travelTimeLayer, weight: travelWeight },
  // Crime is bad, so we'll subtract it instead of adding
  { hexagons: crimeLayer, weight: -crimeWeight },
  { hexagons: cafesLayer, weight: cafesWeight },
];
```

```js
const combinedLayers = (() => {
  const combined = {};
  mapLayers.forEach(({ hexagons, weight }) => {
    Object.keys(hexagons).forEach((hex) => {
      combined[hex] = (combined[hex] || 0) + hexagons[hex] * weight;
    });
  });
  return normalizeLayer(combined);
})();
```

## Utilities

```js
function kmToRadius(km) {
  return Math.floor(km / h3.edgeLength(h3Resolution, h3.UNITS.km));
}
```

```js
function bufferPointsLinear(geojson, radius) {
  const layer = {};
  geojson.features.forEach((feature) => {
    const [lng, lat] = feature.geometry.coordinates;
    const stationIndex = h3.geoToH3(lat, lng, h3Resolution);
    const rings = h3.kRingDistances(stationIndex, radius);
    const step = 1 / (radius + 1);
    rings.forEach((ring, distance) => {
      ring.forEach((h3Index) => {
        layer[h3Index] = (layer[h3Index] || 0) + 1 - distance * step;
      });
    });
  });
  return normalizeLayer(layer);
}
```

```js
function normalizeLayer(layer, baseAtZero = false) {
  const hexagons = Object.keys(layer);
  const max = hexagons.reduce(
    (max, hex) => Math.max(max, layer[hex]),
    -Infinity,
  );
  const min = baseAtZero
    ? hexagons.reduce((min, hex) => Math.min(min, layer[hex]), Infinity)
    : 0;
  hexagons.forEach((hex) => {
    layer[hex] = (layer[hex] - min) / (max - min);
  });
  return layer;
}
```

## Map Rendering

```js
function* map(mapboxgl, mapContainer, config, renderHexes, combinedLayers) {
  let map = this;
  if (!map) {
    map = new mapboxgl.Map({
      container: mapContainer,
      center: [config.lng, config.lat],
      zoom: config.zoom,
      style: "mapbox://styles/mapbox/light-v9",
    });
  }

  yield new Promise((resolve) => {
    if (map.loaded()) resolve(map);
    else map.on("load", () => resolve(map));
  });

  renderHexes(map, combinedLayers);
}
```

```js
function renderHexes(map, hexagons) {
  const geojson = geojson2h3.h3SetToFeatureCollection(
    Object.keys(hexagons),
    (hex) => ({ value: hexagons[hex] }),
  );

  const sourceId = "h3-hexes";
  const layerId = `${sourceId}-layer`;
  let source = map.getSource(sourceId);

  if (!source) {
    map.addSource(sourceId, {
      type: "geojson",
      data: geojson,
    });
    map.addLayer({
      id: layerId,
      source: sourceId,
      type: "fill",
      interactive: false,
      paint: {
        "fill-outline-color": "rgba(0,0,0,0)",
      },
    });
    source = map.getSource(sourceId);
  }

  source.setData(geojson);

  map.setPaintProperty(layerId, "fill-color", {
    property: "value",
    stops: [
      [0, config.colorScale[0]],
      [0.5, config.colorScale[1]],
      [1, config.colorScale[2]],
    ],
  });
  map.setPaintProperty(layerId, "fill-opacity", config.fillOpacity);
}
```

## Config

```js
const config = {
  lng: -122.2,
  lat: 37.7923539,
  zoom: 11,
  fillOpacity: 0.9,
  colorScale: ["#ffffD9", "#50BAC3", "#1A468A"],
  areaThreshold: 0.75,
};
```

## Raw Data

Oakland crime reports, last 90 days. Source: [data.oaklandnet.com](https://data.oaklandnet.com/Public-Safety/90-Day-Crime-Map/kzer-wcj5)

```js
const crime90days = await d3Fetch.json(
  "https://gist.githubusercontent.com/nrabinowitz/d3a5ca3e3e40727595dd137b65058c76/raw/f5ef0fed8972d04a27727ebb50e065265e2d853f/oakland_crime_90days.json",
);
```

Oakland public school locations. Source: [data.oaklandnet.com](https://data.oaklandnet.com/Education/OAKLAND-SCHOOLS/d6pc-iyaw)

```js
const publicSchools = await d3Fetch.json(
  "https://gist.githubusercontent.com/nrabinowitz/d3a5ca3e3e40727595dd137b65058c76/raw/babf7357f15c99a1b2a507a33d332a4a87b7df8d/public_schools.json",
);
```

BART station locations. Source: [bart.gov](https://www.bart.gov/schedules/developers/geo)

```js
const bartStations = await d3Fetch.json(
  "https://gist.githubusercontent.com/nrabinowitz/d3a5ca3e3e40727595dd137b65058c76/raw/8f1a3e30113472404feebc288e83688a6d5cf33d/bart.json",
);
```

Travel times from Oakland to downtown SF by census tract. Source: [movement.uber.com](https://movement.uber.com/explore/san_francisco/travel-times)

```js
const sfTravelTimes = await d3Fetch.json(
  "https://gist.githubusercontent.com/nrabinowitz/d3a5ca3e3e40727595dd137b65058c76/raw/657a9f3b64fedc718c3882cd4adc645ac0b4cfc5/oakland_travel_times.json",
);
```

Oakland points of interest. Source: [uber.com/local](https://www.uber.com/local/us+ca+san_francisco/)

```js
const pois = await d3Fetch.json(
  "https://gist.githubusercontent.com/nrabinowitz/d3a5ca3e3e40727595dd137b65058c76/raw/ded89c2acef426fe3ee59b05096ed1baecf02090/oakland-poi.json",
);
```

## Dependencies

```js
mapboxgl = require("mapbox-gl@0.43.0");
h3 = require("https://bundle.run/h3-js@3.1.0");
geojson2h3 = require("https://bundle.run/geojson2h3@1.0.1");
d3Fetch = require("d3-fetch");
```
````

---

## 6. H3 Radius Lookup

````markdown
# H3 Radius Lookup

You can use H3 for an efficient radius lookup, as long as you're willing to approximate the circle as a k-ring of hexagons (roughly, a large hexagonal shape). This is much faster than a true search by Haversine distance, but less accurate.

## Input

- **H3 Resolution**: 7–10 (default 8). Finer res means more accuracy but more memory usage. Res 8 is roughly a few city blocks in size.
- **Search Radius (Km)**: 0.5–10 (default 4)
- **Grid Radius Calculation Method**: Edge Length or Cell Area

## Logic

### K-Ring Lookup

To use H3 for the radius lookup, you need to index the points of interest by H3 index. If you want this to be efficient, you'd be better off indexing all the points ahead of time.

```js
const lookupMap = bartStations.features.reduce((map, feature) => {
  // Make a map like {[hexagon]: [id, id, ...]}
  const [lon, lat] = feature.geometry.coordinates;
  const h3Index = h3.latLngToCell(lat, lon, res);
  if (!map[h3Index]) map[h3Index] = [];
  map[h3Index].push(feature);
  return map;
}, {});
```

To search, index your search location and get all the H3 indexes within some radius. The functions below demonstrate two methods to go from real-world radius (e.g. meters) to grid radius - one based on edge length, and one based on cell area.

```js
function kRingResults(searchLocation) {
  const lookupIndexes = kRingIndexes(searchLocation);
  // Find all points of interest in the k-ring
  return lookupIndexes.reduce(
    (output, h3Index) => [...output, ...(lookupMap[h3Index] || [])],
    [],
  );
}
```

```js
function kRingIndexesEdge(searchLocation, pad = 0) {
  const origin = h3.latLngToCell(searchLocation.lat, searchLocation.lng, res);
  // Transform the radius from km to grid distance
  const radius =
    Math.floor(
      searchRadiusKm / (h3.getHexagonEdgeLengthAvg(res, h3.UNITS.km) * 2),
    ) + pad;
  return h3.gridDisk(origin, radius);
}
```

```js
function kRingIndexesArea(searchLocation) {
  const origin = h3.latLngToCell(searchLocation.lat, searchLocation.lng, res);
  const originArea = h3.cellArea(origin, h3.UNITS.km2);
  const searchArea = Math.PI * searchRadiusKm * searchRadiusKm;
  let radius = 0;
  let diskArea = originArea;
  while (diskArea < searchArea) {
    radius++;
    const cellCount = 3 * radius * (radius + 1) + 1;
    diskArea = cellCount * originArea;
  }
  return h3.gridDisk(origin, radius);
}
```

### Distance Lookup

One naive alternative is to check every point by Haversine distance, and find those within the radius. This is more accurate, but slower in many cases - it's `O(points)` instead of `O(hexagons)`, and the Haversine calculation is relatively slow compared to H3 indexing and lookup.

```js
function haversineResults(searchLocation) {
  return bartStations.features.filter(
    (feature) =>
      haversineDistance(
        [searchLocation.lng, searchLocation.lat],
        feature.geometry.coordinates,
        { units: "kilometers" },
      ) < searchRadiusKm,
  );
}
```

## Data

BART station locations in GeoJSON format. Source: [bart.gov](https://www.bart.gov/schedules/developers/geo)

```js
const bartStations = await d3Fetch.json(
  "https://gist.githubusercontent.com/nrabinowitz/d3a5ca3e3e40727595dd137b65058c76/raw/8f1a3e30113472404feebc288e83688a6d5cf33d/bart.json",
);
```

## Dependencies

```js
h3 = require("h3-js@4.1.0");
d3Fetch = require("d3-fetch");
geojson2h3 = require("https://bundle.run/geojson2h3@1.0.1");
mapboxgl = require("mapbox-gl@0.43.0");
makeCircle = require("https://bundle.run/@turf/circle@6.0.1"); // .default
haversineDistance = require("https://bundle.run/@turf/distance@6.0.1"); // .default
```
````

---
