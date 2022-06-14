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
(6);
INSERT INTO edge VALUES
(0, 1, 1),
(0, 2, 1),
(0, 4, 1),
(1, 2, 1),
(1, 3, 1),
(2, 3, 1),
(2, 5, 1),
(2, 6, 1),
(3, 0, 1),
(4, 0, 1),
(5, 6, 1),
(6, 3, 1),
(0, 1, 2),
(0, 2, 2),
(0, 4, 2),
(1, 2, 2),
(1, 3, 2),
(2, 3, 2),
(3, 0, 2),
(4, 0, 2),
(5, 6, 2),
(6, 3, 2);

DROP TABLE IF EXISTS pagerank_out, pagerank_out_summary;
SELECT madlib.pagerank(
                       'vertex',                        -- Vertex table
                       'node_id',                       -- Vertex id column
                       'edge',                          -- Edge table
                       'src=conn_src, dest=conn_dest',  -- Comma delimted string of edge arguments
                       'pagerank_out');                 -- Output table of PageRank
SELECT * FROM pagerank_out ORDER BY pagerank DESC;

SELECT * FROM pagerank_out_summary;

DROP TABLE IF EXISTS pagerank_out, pagerank_out_summary;
SELECT madlib.pagerank(
                       'vertex',                        -- Vertex table
                       'node_id',                       -- Vertex id column
                       'edge',                          -- Edge table
                       'src=conn_src, dest=conn_dest',  -- Comma delimted string of edge arguments
                       'pagerank_out',                  -- Output table of PageRank
                       0.5);                            -- Damping factor
SELECT * FROM pagerank_out ORDER BY pagerank DESC;

DROP TABLE IF EXISTS pagerank_out, pagerank_out_summary;
SELECT madlib.pagerank(
                       'vertex',                        -- Vertex table
                       'node_id',                       -- Vertex id column
                       'edge',                          -- Edge table
                       'src=conn_src, dest=conn_dest',  -- Comma delimted string of edge arguments
                       'pagerank_out',                  -- Output table of PageRank
                       NULL,                            -- Default damping factor (0.85)
                       NULL,                            -- Default max iters (100)
                       0.00000001,                      -- Threshold
                       'user_id');                      -- Grouping column name
SELECT * FROM pagerank_out ORDER BY user_id, pagerank DESC;

SELECT * FROM pagerank_out_summary ORDER BY user_id;

DROP TABLE IF EXISTS pagerank_out, pagerank_out_summary;
SELECT madlib.pagerank(
                       'vertex',                        -- Vertex table
                       'node_id',                       -- Vertex id column
                       'edge',                          -- Edge table
                       'src=conn_src, dest=conn_dest',  -- Comma delimted string of edge arguments
                       'pagerank_out',                  -- Output table of PageRank
                        NULL,                           -- Default damping factor (0.85)
                        NULL,                           -- Default max iters (100)
                        NULL,                           -- Default Threshold
                        NULL,                           -- No Grouping
                       '{2,4}');                        -- Personalization vertices
SELECT * FROM pagerank_out ORDER BY pagerank DESC;
SELECT * FROM pagerank_out_summary;

DROP TABLE IF EXISTS vertex_multicol_pagerank, edge_multicol_pagerank;
CREATE TABLE vertex_multicol_pagerank(
    node_id_major BIGINT,
    node_id_minor BIGINT
);
CREATE TABLE edge_multicol_pagerank(
    conn_src_major BIGINT,
    conn_dest_major BIGINT,
    user_id_major BIGINT,
    conn_src_minor BIGINT,
    conn_dest_minor BIGINT,
    user_id_minor BIGINT
);
INSERT INTO vertex_multicol_pagerank VALUES
(0, 0),
(1, 1),
(2, 2),
(3, 3),
(4, 4),
(5, 5),
(6, 6);
INSERT INTO edge_multicol_pagerank VALUES
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

DROP TABLE IF EXISTS pagerank_multicol_out, pagerank_multicol_out_summary;
SELECT madlib.pagerank(
                       'vertex_multicol_pagerank',                                                      -- Vertex table
                       '[node_id_major,node_id_minor]',                                                 -- Vertex id column
                       'edge_multicol_pagerank',                                                        -- Edge table
                       'src=[conn_src_major,conn_src_minor], dest=[conn_dest_major,conn_dest_minor]',   -- Comma delimted string of edge arguments
                       'pagerank_multicol_out',                                                         -- Output table of PageRank
                        NULL,                                                                           -- Default damping factor (0.85)
                        NULL,                                                                           -- Default max iters (100)
                        NULL,                                                                           -- Default Threshold
                       'user_id_major,user_id_minor',                                                   -- Grouping Columns
                       '{{2,2},{4,4}}');                                                                -- Personalization vertices
SELECT * FROM pagerank_multicol_out ORDER BY pagerank DESC;
SELECT * FROM pagerank_multicol_out_summary;
