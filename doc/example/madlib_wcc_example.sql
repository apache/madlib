/* ----------------------------------------------------------------------- *//**
 *
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 *
 *//* ----------------------------------------------------------------------- */

DROP TABLE IF EXISTS vertex, edge;
CREATE TABLE vertex(
    node_id INTEGER
);
CREATE TABLE edge(
    conn_src INTEGER,
    conn_dest INTEGER,
    user_id INTEGER
);
INSERT INTO vertex VALUES
(0),
(1),
(2),
(3),
(4),
(5),
(6),
(10),
(11),
(12),
(13),
(14),
(15),
(16);
INSERT INTO edge VALUES
(0, 1, 1),
(0, 2, 1),
(1, 2, 1),
(1, 3, 1),
(2, 3, 1),
(2, 5, 1),
(2, 6, 1),
(3, 0, 1),
(5, 6, 1),
(6, 3, 1),
(10, 11, 2),
(10, 12, 2),
(11, 12, 2),
(11, 13, 2),
(12, 13, 2),
(13, 10, 2),
(15, 16, 2),
(15, 14, 2);

DROP TABLE IF EXISTS wcc_out, wcc_out_summary;
SELECT madlib.weakly_connected_components(
    'vertex',                        -- Vertex table
    'node_id',                       -- Vertex id column
    'edge',                          -- Edge table
    'src=conn_src, dest=conn_dest',  -- Comma delimted string of edge arguments
    'wcc_out');                      -- Output table of weakly connected components
SELECT * FROM wcc_out ORDER BY component_id, id;

DROP TABLE IF EXISTS wcc_out, wcc_out_summary;
SELECT madlib.weakly_connected_components(
    'vertex',                       -- Vertex table
    'node_id',                      -- Vertex id column
    'edge',                         -- Edge table
    'src=conn_src, dest=conn_dest', -- Comma delimted string of edge arguments
    'wcc_out',                      -- Output table of weakly connected components
    'user_id');                     -- Grouping column name
SELECT * FROM wcc_out ORDER BY user_id, component_id, id;

DROP TABLE IF EXISTS largest_cpt_table;
SELECT madlib.graph_wcc_largest_cpt(
                         'wcc_out',             -- WCC output table
                         'largest_cpt_table');  -- output table containing largest component ID
SELECT * FROM largest_cpt_table ORDER BY component_id;

DROP TABLE IF EXISTS histogram_table;
SELECT madlib.graph_wcc_histogram(
                         'wcc_out',           -- WCC output table
                         'histogram_table');  -- output table containing the histogram of vertices
SELECT * FROM histogram_table ORDER BY component_id;

DROP TABLE IF EXISTS vc_table;
SELECT madlib.graph_wcc_vertex_check(
                         'wcc_out',    -- WCC output table
                         '14,15',      -- Pair of vertex IDs
                         'vc_table');  -- output table containing components that contain the two vertices
SELECT * FROM vc_table ORDER BY component_id;

DROP TABLE IF EXISTS reach_table;
SELECT madlib.graph_wcc_reachable_vertices(
                         'wcc_out',         -- WCC output table
                         '0',               -- source vertex
                         'reach_table');    -- output table containing all vertices reachable from source vertex
SELECT * FROM reach_table ORDER BY component_id, dest;

DROP TABLE IF EXISTS count_table;
SELECT madlib.graph_wcc_num_cpts(
                         'wcc_out',       -- WCC output table
                         'count_table');  -- output table containing number of components per group
SELECT * FROM count_table;

DROP TABLE IF EXISTS vertex_multicol_wcc, edge_multicol_wcc;
CREATE TABLE vertex_multicol_wcc(
    node_id_major BIGINT,
    node_id_minor BIGINT
);
CREATE TABLE edge_multicol_wcc(
    conn_src_major BIGINT,
    conn_dest_major BIGINT,
    user_id_major BIGINT,
    conn_src_minor BIGINT,
    conn_dest_minor BIGINT,
    user_id_minor BIGINT
);
INSERT INTO vertex_multicol_wcc VALUES
(0, 0),
(1, 1),
(2, 2),
(3, 3),
(4, 4),
(5, 5),
(6, 6);
INSERT INTO edge_multicol_wcc VALUES
(0, 1, 1, 0, 1, 1),
(0, 2, 1, 0, 2, 1),
(0, 4, 1, 0, 4, 1),
(1, 2, 1, 1, 2, 1),
(1, 3, 1, 1, 3, 1),
(2, 3, 1, 2, 3, 1),
(2, 5, 1, 2, 5, 1),
(2, 6, 1, 2, 6, 1),
(3, 0, 1, 3, 0, 1),
(4, 0, 1, 4, 0, 1),
(5, 6, 1, 5, 6, 1),
(6, 3, 1, 6, 3, 1),
(0, 1, 2, 0, 1, 2),
(0, 2, 2, 0, 2, 2),
(0, 4, 2, 0, 4, 2),
(1, 2, 2, 1, 2, 2),
(1, 3, 2, 1, 3, 2),
(2, 3, 2, 2, 3, 2),
(3, 0, 2, 3, 0, 2),
(4, 0, 2, 4, 0, 2),
(5, 6, 2, 5, 6, 2),
(6, 3, 2, 6, 3, 2);

DROP TABLE IF EXISTS wcc_multicol_out, wcc_multicol_out_summary;
SELECT madlib.weakly_connected_components(
    'vertex_multicol_wcc',                                                          -- Vertex table
    '[node_id_major,node_id_minor]',                                                -- Vertex id column
    'edge_multicol_wcc',                                                            -- Edge table
    'src=[conn_src_major,conn_src_minor], dest=[conn_dest_major,conn_dest_minor]',  -- Comma delimted string of edge arguments
    'wcc_multicol_out',                                                             -- Output table of weakly connected components
    'user_id_major,user_id_minor');                                                 -- Grouping column name
SELECT * FROM wcc_multicol_out ORDER BY user_id_major, user_id_minor, component_id, id;
