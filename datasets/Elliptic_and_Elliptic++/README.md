# Elliptic / Elliptic++ / Elliptic2 — Detailed Dataset + Documentation Brief

Gareth Block provides background to GPT-5.5 on Arango + Databricks, asking for its views on applicable datasets that show ArangoAI on streaming-scale architectures where Databricks agents treat ArangoDB as their primary graph memory. 

Our Arango + Databricks approach treats medallion flows not as fixed pipelines but as a **dynamic substrate** for agentic context. **GraphRAG** anchors anomaly workflows, surfacing normal patterns, tightening GraphML detection pipelines, and wiring alerts to graph visualization as events arrive. We use the concept of "graphlets"—graph-shaped extracts from Delta tables (for example Gold)—plus event recognition, so ArangoAI can reshape medallion behavior continuously in production. Shared context feeds back into Silver-to-Gold transforms upstream so they stay aligned with downstream needs: analyst priorities, online GraphML drift, and evolving agent workflows.

**Elliptic Bitcoin dataset family** is one motivating scenario.  


## 1. Executive summary

The **Elliptic Bitcoin dataset family** is a public anti-money-laundering dataset ecosystem for detecting illicit activity in Bitcoin transaction graphs. It is useful for a **financial-crime graph analytics demo**, especially if the platform objective is to show:

```text
Bitcoin transaction stream
→ typed graph normalization
→ temporal graphlet accumulation
→ heterogeneous GNN / GraphSAGE scoring
→ ArangoDB graph persistence
→ GraphRAG-backed AML explanation
→ analyst triage visualization
```

However, the three variants have different levels of fit:

| Dataset               | Best use                                      | Fit for your architecture |
| --------------------- | --------------------------------------------- | ------------------------: |
| **Original Elliptic** | Baseline transaction classification           |                    Medium |
| **Elliptic++**        | Heterogeneous wallet + transaction graph demo |                      High |
| **Elliptic2**         | Subgraph / graphlet AML detection             |                 Very high |

The original Elliptic dataset is historically important and widely used, but it is limited for your purposes because it is mostly a **transaction-node classification benchmark** with anonymized/engineered features. Elliptic++ adds **wallet-address / actor-level structure**, making it much better for heterogeneous graphlets. Elliptic2 is the closest conceptual match because it reframes AML as a **subgraph representation learning** problem over labeled Bitcoin cluster subgraphs. ([PyG Documentation][1])

---

# 2. Primary source links

## 2.1 Original Elliptic dataset — Kaggle

**Purpose:** Public Bitcoin transaction graph classification dataset.

**Use in your system:**
Good for a first AML graph demo, baseline classifier comparison, Databricks ingestion, and transaction-level temporal graph construction.

**Link:**
[https://www.kaggle.com/datasets/ellipticco/elliptic-data-set](https://www.kaggle.com/datasets/ellipticco/elliptic-data-set)

PyTorch Geometric describes the original Elliptic Bitcoin dataset as **203,769 transaction nodes** and **234,355 directed payment-flow edges**, with about **4,545 illicit nodes**, **42,019 licit nodes**, and the remaining transactions unknown. It maps Bitcoin transactions to real entities categorized as licit services versus illicit activity such as scams, malware, ransomware, terrorist organizations, and Ponzi schemes. ([PyG Documentation][1])

---

## 2.2 Elliptic public release article

**Purpose:** Original release context from Elliptic.

**Use in your system:**
GraphRAG background document explaining why the dataset exists and what kind of financial-crime problem it represents.

**Link:**
[https://www.elliptic.co/blog/elliptic-dataset-cryptocurrency-financial-crime](https://www.elliptic.co/blog/elliptic-dataset-cryptocurrency-financial-crime)

Elliptic says the dataset includes roughly **200,000 Bitcoin transactions** with a total value of **$6 billion**, labeled as licit or illicit where known. The original release was intended to motivate community research into detecting illicit cryptocurrency transactions using blockchain-only data. ([Elliptic][2])

---

## 2.3 Original Elliptic paper

**Purpose:** Baseline ML/GNN paper for financial forensics.

**Use in your system:**
Use this as a baseline modeling document and as evidence for why graph-based structure is useful for AML.

**Link:**
[https://arxiv.org/abs/1908.02591](https://arxiv.org/abs/1908.02591)

The paper is commonly cited as:

```text
Anti-Money Laundering in Bitcoin: Experimenting with Graph Convolutional Networks for Financial Forensics
```

It is the source of the original benchmark framing: transaction nodes, payment-flow edges, licit/illicit/unknown classes, and comparison of classical ML versus GNN models. PyTorch Geometric explicitly ties its `EllipticBitcoinDataset` loader to this paper. ([PyG Documentation][1])

---

## 2.4 Elliptic++ paper

**Purpose:** Extended dataset with transactions plus wallet addresses / actors.

**Use in your system:**
Best practical target for your **heterogeneous graphlet** AML demo.

**Link:**
[https://arxiv.org/abs/2306.06108](https://arxiv.org/abs/2306.06108)

Elliptic++ extends the original dataset to include **over 822k Bitcoin wallet addresses**, **56 wallet features**, and **1.27M temporal interactions**. It supports four graph views: transaction-to-transaction, address-to-address, address-transaction, and user-entity graphs. ([arXiv][3])

---

## 2.5 Elliptic++ GitHub repository

**Purpose:** Dataset guide, download pointer, tutorials, and dataset summary.

**Use in your system:**
Primary downloader-agent manifest for Elliptic++.

**Link:**
[https://github.com/git-disl/EllipticPlusPlus](https://github.com/git-disl/EllipticPlusPlus)

The repository states that Elliptic++ consists of **203k Bitcoin transactions** and **822k wallet addresses** to support both fraudulent transaction detection and illicit actor detection. It provides separate **Transactions Dataset** and **Actors Dataset** folders, tutorial notebooks, and a Google Drive link for the dataset. ([GitHub][4])

---

## 2.6 Elliptic2 dataset — Kaggle

**Purpose:** Large subgraph AML dataset.

**Use in your system:**
Best target if the demo is explicitly about **graphlet/subgraph scoring** rather than transaction-node classification.

**Link:**
[https://www.kaggle.com/datasets/ellipticco/elliptic2-data-set](https://www.kaggle.com/datasets/ellipticco/elliptic2-data-set)

Kaggle describes Elliptic2 as a large graph dataset with a background graph of **49M node clusters** and **196M edge transactions**. ([Kaggle][5])

---

## 2.7 Elliptic2 paper

**Purpose:** Subgraph representation learning for money-laundering detection.

**Use in your system:**
Primary theoretical support for “AML is a graphlet/subgraph problem.”

**Link:**
[https://arxiv.org/abs/2404.19109](https://arxiv.org/abs/2404.19109)

The Elliptic2 paper introduces **122K labeled subgraphs of Bitcoin clusters** inside a much larger background graph of **49M node clusters** and **196M edge transactions**, explicitly arguing that AML is better modeled as a **subgraph representation learning** problem than a single-node classification problem. ([arXiv][6])

---

## 2.8 Elliptic2 GitHub repository

**Purpose:** Official usage guide and preprocessing code.

**Use in your system:**
Primary implementation reference for Elliptic2 experiments.

**Link:**
[https://github.com/MITIBMxGraph/Elliptic2](https://github.com/MITIBMxGraph/Elliptic2)

The repository identifies the required dataset files as:

```text
dataset/
  background_edges.csv
  background_nodes.csv
  connected_components.csv
  edges.csv
  nodes.csv
```

It also includes preprocessing paths for **GLASS**, **GNNSeg**, and **Sub2Vec**, including scripts that generate `edge_list.txt`, `subgraph.pth`, `n2id.pkl`, `sub2vec_input`, and `label.pkl`. ([GitHub][7])

---

## 2.9 PyTorch Geometric loader

**Purpose:** Standard loader for original Elliptic.

**Use in your system:**
Useful for baseline experiments, sanity checks, and model comparison.

**Link:**
[https://pytorch-geometric.readthedocs.io/en/2.5.0/generated/torch_geometric.datasets.EllipticBitcoinDataset.html](https://pytorch-geometric.readthedocs.io/en/2.5.0/generated/torch_geometric.datasets.EllipticBitcoinDataset.html)

PyTorch Geometric provides `EllipticBitcoinDataset` as an `InMemoryDataset`, which is useful for rapid prototyping but does not solve the richer heterogeneous graphlet problem by itself. ([PyG Documentation][1])

---

# 3. Dataset-family comparison

| Dimension                    |                      Original Elliptic |                                        Elliptic++ |                                                Elliptic2 |
| ---------------------------- | -------------------------------------: | ------------------------------------------------: | -------------------------------------------------------: |
| Main unit                    |                       Transaction node |                Transaction + wallet/address/actor |                               Subgraph / Bitcoin cluster |
| Graph type                   |              Directed transaction flow |                    Multi-view heterogeneous graph |              Labeled subgraphs in large background graph |
| Temporal structure           |                          49 time steps |                                     49 time steps |            Large-scale temporal blockchain graph context |
| Labels                       | Licit / illicit / unknown transactions | Licit / illicit / unknown transactions and actors |                                        Labeled subgraphs |
| Best ML task                 |                    Node classification |  Node/actor classification, hetero graph learning |        Subgraph classification / graphlet representation |
| Fit for Bronze/Silver/Gold   |                                   Good |                                            Strong |                                 Strong, but larger-scale |
| Fit for GraphSAGE            |                               Moderate |                                            Strong | Strong, but may require subgraph models beyond GraphSAGE |
| Fit for GraphRAG             |                    Medium if augmented |                          Medium-high if augmented |                       High if paired with AML typologies |
| Fit for Arango visualization |                                 Medium |                                              High |                                                     High |
| Demo complexity              |                             Low-medium |                                            Medium |                                                     High |

---

# 4. Original Elliptic dataset synopsis

## 4.1 Core structure

The original Elliptic dataset is a Bitcoin transaction graph:

```text
Node = Bitcoin transaction
Edge = directed payment flow between transactions
Label = licit / illicit / unknown
Time = one of 49 discrete time steps
Features = anonymized transaction and neighborhood features
```

PyTorch Geometric reports:

| Field                        |                  Value |
| ---------------------------- | ---------------------: |
| Transaction nodes            |                203,769 |
| Directed payment-flow edges  |                234,355 |
| Illicit nodes                |                  4,545 |
| Licit nodes                  |                 42,019 |
| Unknown nodes                | Remaining transactions |
| Approximate illicit fraction |                    ~2% |

([PyG Documentation][1])

## 4.2 What it supports well

Original Elliptic supports:

```text
transaction classification
baseline GNN experiments
temporal holdout evaluation
class-imbalance analysis
alert-triage visualization
Databricks ingestion demo
basic Arango transaction-flow graph
```

## 4.3 What it does not support well

Original Elliptic is weak for your full architecture because:

| Limitation                              | Impact                                   |
| --------------------------------------- | ---------------------------------------- |
| Transaction-only node abstraction       | Weak heterogeneous graph story           |
| Many engineered/anonymized features     | Weak explanation story                   |
| Coarse labels                           | Weak AML typology mapping                |
| Unknown labels dominate                 | Complicates evaluation                   |
| Common splits may leak information      | Benchmark claims need caution            |
| No built-in natural-language narratives | GraphRAG corpus must be externally built |

A 2026 DFRWS paper argues that the original Elliptic feature-construction process was not fully disclosed, limiting reproducibility and operational use because practitioners cannot compute the same required features for new investigations. It also argues that common train/test splits may not be properly isolated. ([DFRWS][8])

## 4.4 Recommended role

Use original Elliptic as:

```text
baseline AML graph classification dataset
starter ingestion target
control case for GNN vs classical ML
transaction-level demo
```

Do **not** make it the flagship demo for heterogeneous temporal graphlets.

---

# 5. Elliptic++ synopsis

## 5.1 Core structure

Elliptic++ extends original Elliptic with wallet-address / actor context. It includes both a transaction dataset and an actors dataset. The GitHub summary reports:

### Transactions dataset

| Field                |   Value |
| -------------------- | ------: |
| Transaction nodes    | 203,769 |
| Money-flow edges     | 234,355 |
| Time steps           |      49 |
| Illicit transactions |   4,545 |
| Licit transactions   |  42,019 |
| Unknown transactions | 157,205 |
| Features             |     183 |

### Actors / wallet-address dataset

| Field                             |     Value |
| --------------------------------- | --------: |
| Wallet addresses                  |   822,942 |
| Temporal interaction nodes        | 1,268,260 |
| Address-address edges             | 2,868,964 |
| Address-transaction-address edges | 1,314,241 |
| Time steps                        |        49 |
| Illicit actors                    |    14,266 |
| Licit actors                      |   251,088 |
| Unknown actors                    |   557,588 |
| Features                          |        56 |

([GitHub][4])

## 5.2 Graph views

The Elliptic++ paper describes four graph views:

| Graph view                 | Meaning                                                                 | Use in your architecture       |
| -------------------------- | ----------------------------------------------------------------------- | ------------------------------ |
| Transaction-to-transaction | Money flow between Bitcoin transactions                                 | Baseline transaction graph     |
| Address-to-address         | Interactions between Bitcoin addresses                                  | Actor interaction graph        |
| Address-transaction        | Bipartite flow from input addresses to transactions to output addresses | Best hetero graphlet substrate |
| User-entity graph          | Clusters of addresses representing likely unique users                  | Actor / entity-level AML graph |

([arXiv][3])

## 5.3 Why Elliptic++ is materially better

Elliptic++ supports a proper heterogeneous AML ontology:

```text
Address
Transaction
Actor / EntityCluster
TemporalInteraction
Flow
Graphlet
RiskPattern
EvidenceDocument
```

And relation types such as:

```text
INPUT_TO
OUTPUT_FROM
SENDS_TO
RECEIVES_FROM
CLUSTERED_AS
INTERACTS_WITH
PART_OF_TIME_STEP
PART_OF_GRAPHLET
MATCHES_AML_PATTERN
SUPPORTED_BY_DOC
```

This makes it much more appropriate for your Databricks + Arango + GraphRAG architecture.

## 5.4 Recommended role

Use Elliptic++ as the **primary AML MVP** if you want manageable scale and heterogeneous structure.

It is the best compromise between:

```text
public availability
size
heterogeneous graph support
temporal structure
reasonable engineering effort
demo value
```

---

# 6. Elliptic2 synopsis

## 6.1 Core structure

Elliptic2 is not just a larger Elliptic. It changes the modeling unit from individual transaction nodes to **subgraphs**.

The paper introduces:

| Field                              | Value |
| ---------------------------------- | ----: |
| Labeled subgraphs                  |  122K |
| Background graph node clusters     |   49M |
| Background graph edge transactions |  196M |

([arXiv][6])

The official GitHub usage guide expects these files:

```text
dataset/
  background_edges.csv
  background_nodes.csv
  connected_components.csv
  edges.csv
  nodes.csv
```

([GitHub][7])

## 6.2 Why Elliptic2 is the closest conceptual match

Elliptic2 explicitly supports:

```text
subgraph classification
money-laundering shape detection
graphlet-level representation learning
large background graph context
AML pattern discovery
```

That maps directly to your desired architecture:

```text
Bronze blockchain records
→ Silver typed clusters / transactions / flows
→ Gold AML graphlets
→ subgraph embedding
→ laundering-shape score
→ GraphRAG explanation
→ analyst-priority case
```

## 6.3 Model ecosystem

The Elliptic2 repository includes preprocessing support for:

| Model family | Role                                       |
| ------------ | ------------------------------------------ |
| **GLASS**    | Subgraph learning                          |
| **GNNSeg**   | Subgraph / segment-oriented graph modeling |
| **Sub2Vec**  | Subgraph embedding baseline                |

The repository gives preprocessing instructions for creating model-specific artifacts such as `edge_list.txt`, `subgraph.pth`, `n2id.pkl`, `sub2vec_input`, and `label.pkl`. ([GitHub][7])

## 6.4 Recommended role

Use Elliptic2 as the **flagship AML graphlet demo** once the pipeline is mature.

It is stronger than Elliptic++ for the narrative:

> “Money laundering is not a single suspicious transaction. It is a suspicious local structure evolving through a financial network.”

---

# 7. Natural-language support for GraphRAG

The Elliptic datasets are weaker than DARPA TC in built-in natural-language material. The blockchain data itself is graph-rich but semantically sparse. Therefore, the GraphRAG layer should be externally augmented.

## 7.1 Tier 1 — Mandatory corpus

| Source                             | Role                                            |
| ---------------------------------- | ----------------------------------------------- |
| Original Elliptic paper            | Baseline dataset and model framing              |
| Elliptic release article           | Business and AML context                        |
| Elliptic++ paper                   | Heterogeneous graph and actor-level AML framing |
| Elliptic++ GitHub README/tutorials | Dataset schema, tutorials, download guidance    |
| Elliptic2 paper                    | Subgraph AML theory                             |
| Elliptic2 GitHub README            | Model preprocessing and file layout             |
| Kaggle dataset cards               | Dataset access and license/context              |
| PyTorch Geometric loader docs      | Baseline implementation details                 |

## 7.2 Tier 2 — AML doctrine / regulatory corpus

Use these to make GraphRAG explanations substantive:

| Source family                               | Use                                            |
| ------------------------------------------- | ---------------------------------------------- |
| FATF virtual asset guidance                 | AML regulatory framing and virtual-asset risk  |
| FinCEN advisories                           | Suspicious activity indicators                 |
| OFAC sanctions guidance                     | Sanctions exposure / wallet screening context  |
| Chainalysis / Elliptic / TRM public reports | Crypto laundering typologies and case examples |
| Exchange compliance guides                  | KYC/AML operational workflow                   |
| Academic AML papers                         | Modeling justification                         |
| Blockchain forensic explainers              | Transaction-flow interpretation                |

## 7.3 Tier 3 — Pattern library corpus

Use these to convert prose into graph patterns:

| Pattern source                | Example use                           |
| ----------------------------- | ------------------------------------- |
| AML typology reports          | Layering, placement, integration      |
| Blockchain laundering reports | Peel chains, mixers, bridge hops      |
| Sanctions case reports        | Exposure to sanctioned entities       |
| Ransomware reports            | Ransom payment flow and consolidation |
| Darknet marketplace reports   | Market deposits/withdrawals           |
| Crypto exchange SAR guidance  | Suspicious behavioral indicators      |

---

# 8. Proposed AML ontology

## 8.1 Node types

```text
Transaction
Address
Wallet
Actor
EntityCluster
Service
Exchange
Mixer
DarknetMarket
RansomwareActor
SanctionedEntity
Flow
TimeStep
TemporalWindow
Graphlet
AMLPattern
Typology
EvidenceDocument
EvidenceChunk
ModelRun
Alert
Case
```

## 8.2 Edge types

```text
INPUT_TO
OUTPUT_FROM
PAYS_TO
RECEIVES_FROM
FUNDS_FLOW_TO
CLUSTERED_WITH
CONTROLLED_BY
INTERACTS_WITH
DEPOSITS_TO
WITHDRAWS_FROM
USES_SERVICE
PART_OF_TIME_STEP
PART_OF_WINDOW
PART_OF_GRAPHLET
MATCHES_PATTERN
SIMILAR_TO_GRAPHLET
SUPPORTED_BY_CHUNK
SCORED_BY_MODEL
GENERATED_ALERT
```

## 8.3 Example graphlet

```text
Address A
  → Transaction T1
  → Address B
  → Transaction T2
  → Address C
  → Exchange Deposit E

Graphlet properties:
  time window = 3 hours
  hop count = 3
  fan-out = high
  known-risk proximity = 1 hop
  amount fragmentation = high
  destination service = exchange
```

---

# 9. Bronze / Silver / Gold architecture

## 9.1 Bronze layer

Bronze should preserve raw dataset structure.

```text
bronze_elliptic_raw_files
bronze_elliptic_transactions
bronze_elliptic_edges
bronze_elliptic_classes
bronze_elliptic_features

bronze_ellipticpp_transactions
bronze_ellipticpp_addresses
bronze_ellipticpp_actor_edges
bronze_ellipticpp_address_transaction_edges

bronze_elliptic2_background_nodes
bronze_elliptic2_background_edges
bronze_elliptic2_nodes
bronze_elliptic2_edges
bronze_elliptic2_connected_components
```

## 9.2 Silver layer

Silver normalizes into a common AML graph ontology.

```text
silver_aml_transaction
silver_aml_address
silver_aml_entity_cluster
silver_aml_flow_edge
silver_aml_time_step
silver_aml_label
silver_aml_feature_vector
silver_aml_dataset_lineage
silver_aml_document_chunk
```

## 9.3 Gold layer

Gold should hold graphlets, embeddings, scores, and explanations.

```text
gold_aml_graphlet
gold_aml_graphlet_node
gold_aml_graphlet_edge
gold_aml_graphlet_feature
gold_aml_graphlet_embedding
gold_aml_pattern_match
gold_aml_risk_score
gold_aml_explanation
gold_aml_alert
gold_aml_case
```

---

# 10. Downloader-agent requirements

## 10.1 Objective

The downloader agent should support three acquisition paths:

```text
1. Kaggle download for original Elliptic and Elliptic2.
2. GitHub + Google Drive download for Elliptic++.
3. GitHub clone for model/preprocessing repositories.
```

## 10.2 Required source targets

```text
Original Elliptic:
  https://www.kaggle.com/datasets/ellipticco/elliptic-data-set

Elliptic++:
  https://github.com/git-disl/EllipticPlusPlus
  linked Google Drive dataset from repository

Elliptic2:
  https://www.kaggle.com/datasets/ellipticco/elliptic2-data-set
  https://github.com/MITIBMxGraph/Elliptic2

Supporting docs:
  https://arxiv.org/abs/1908.02591
  https://arxiv.org/abs/2306.06108
  https://arxiv.org/abs/2404.19109
  https://www.elliptic.co/blog/elliptic-dataset-cryptocurrency-financial-crime
```

## 10.3 Recommended local layout

```text
elliptic_family/
  sources/
    kaggle/
      elliptic/
      elliptic2/
    github/
      EllipticPlusPlus/
      Elliptic2/
    drive/
      ellipticplusplus/

  docs/
    original_elliptic/
      elliptic_release_article.md
      original_paper.pdf
      kaggle_dataset_card.md
    ellipticplusplus/
      paper.pdf
      github_readme.md
      tutorials/
    elliptic2/
      paper.pdf
      github_readme.md
      kaggle_dataset_card.md
    aml_corpus/
      fatf/
      fincen/
      ofac/
      elliptic_reports/
      chainalysis_reports/
      academic/

  raw/
    original_elliptic/
    ellipticplusplus/
    elliptic2/

  derived/
    parquet/
    delta/
    graphlets/
    embeddings/
    explanations/

  manifests/
    files.csv
    files.json
    checksums.sha256
    source_catalog.json
    ingestion_status.json
```

## 10.4 Metadata per file

```json
{
  "dataset_family": "elliptic",
  "dataset_variant": "original | ellipticplusplus | elliptic2",
  "source_url": "...",
  "relative_path": "...",
  "file_name": "...",
  "file_type": "csv | zip | parquet | pdf | md | py | ipynb",
  "size_bytes": 0,
  "sha256": "...",
  "download_time_utc": "...",
  "source_modified_time": "...",
  "parse_strategy": "csv | kaggle_zip | github_text | pdf_text | notebook",
  "semantic_role": "transactions | edges | labels | docs | model_code | graphlets",
  "status": "downloaded | parsed | failed | skipped"
}
```

---

# 11. Graphlet accumulation framework

## 11.1 Graphlet anchors

| Anchor                      | Graphlet type                    |
| --------------------------- | -------------------------------- |
| Transaction                 | Local transaction-flow graphlet  |
| Address                     | Wallet neighborhood graphlet     |
| EntityCluster               | Actor behavior graphlet          |
| TimeStep                    | Temporal slice graphlet          |
| Exchange deposit            | Cash-out graphlet                |
| Known illicit label         | Ground-truth anchored graphlet   |
| Unknown high-risk node      | Candidate investigation graphlet |
| Subgraph label in Elliptic2 | Supervised AML graphlet          |

## 11.2 Graphlet policies

```text
k-hop neighborhood around transaction
k-hop neighborhood around address
rolling time-window around actor
fan-in/fan-out motif around transaction
service-deposit path graphlet
known-illicit-proximity graphlet
subgraph-component graphlet from Elliptic2
```

## 11.3 Example Gold graphlet record

```json
{
  "graphlet_id": "aml_graphlet_000001",
  "dataset_variant": "ellipticplusplus",
  "anchor_type": "address",
  "anchor_id": "addr_...",
  "time_step": 17,
  "window_start": "...",
  "window_end": "...",
  "node_counts": {
    "address": 42,
    "transaction": 19,
    "entity_cluster": 3
  },
  "edge_counts": {
    "input_to": 31,
    "output_from": 28,
    "pays_to": 44
  },
  "motif_features": {
    "fan_out": 12,
    "fan_in": 5,
    "max_path_length": 4,
    "known_illicit_distance": 1
  },
  "labels": {
    "contains_illicit": true,
    "anchor_label": "unknown"
  },
  "lineage": {
    "source_dataset": "Elliptic++",
    "source_files": ["..."]
  }
}
```

---

# 12. GNN / GraphSAGE design

## 12.1 Original Elliptic

Use for baseline homogeneous graph learning:

```text
Data.x = transaction feature matrix
Data.edge_index = payment-flow edges
Data.y = licit / illicit / unknown
```

Models:

```text
Logistic Regression
Random Forest
XGBoost
GCN
GAT
GraphSAGE
Temporal split baseline
```

## 12.2 Elliptic++

Use heterogeneous graph learning:

```text
HeteroData["transaction"].x
HeteroData["address"].x
HeteroData["entity_cluster"].x
HeteroData["time_step"].x

("address", "input_to", "transaction")
("transaction", "output_to", "address")
("transaction", "flows_to", "transaction")
("address", "interacts_with", "address")
("address", "clustered_as", "entity_cluster")
("transaction", "in_time_step", "time_step")
```

This is the best target for **heterogeneous GraphSAGE** or relation-specific message passing.

## 12.3 Elliptic2

Use subgraph learning:

```text
Subgraph object
  nodes
  edges
  background context
  label
  derived features
  embedding
```

Candidate models:

```text
GLASS
GNNSeg
Sub2Vec
GraphSAGE over extracted subgraphs
GIN / GAT over subgraph neighborhoods
Heterogeneous subgraph encoder if entity types are reconstructed
```

Elliptic2’s official repository specifically provides preprocessing paths for GLASS, GNNSeg, and Sub2Vec. ([GitHub][7])

---

# 13. Pattern-generation framework

## 13.1 Seed AML graph patterns

### Pattern 1 — Peel-chain candidate

```text
Address A
  → Transaction T1
  → Address B
  → Transaction T2
  → Address C
  → Transaction T3
  → Address D

where:
  amounts gradually decrease
  time gaps are short
  path length > threshold
  destination eventually touches service/exchange
```

### Pattern 2 — Fan-out layering

```text
Address A
  → many Transactions
  → many output Addresses

where:
  fan_out is high
  amounts are fragmented
  outputs occur in same or adjacent time step
```

### Pattern 3 — Fan-in consolidation

```text
many Addresses
  → many Transactions
  → Address C

where:
  fan_in is high
  sources are weakly connected
  destination becomes central
```

### Pattern 4 — Illicit-proximity cash-out

```text
Illicit-labeled entity
  → transaction path length <= k
  → exchange/service deposit

where:
  path occurs within temporal window
  intermediate nodes are unknown
```

### Pattern 5 — Unknown actor resembling illicit actor

```text
Unknown Address / EntityCluster
  has graphlet embedding close to known illicit graphlets
  and structural motif matches laundering typology
```

---

# 14. GraphRAG explanation framework

## 14.1 Explanation pipeline

```text
graphlet scored
→ retrieve graphlet topology summary
→ retrieve nearest known illicit graphlets
→ retrieve AML typology documents
→ retrieve Elliptic/Elliptic++/Elliptic2 dataset docs
→ retrieve relevant regulatory guidance
→ generate explanation
→ attach evidence chunks
→ store in Gold + Arango
```

## 14.2 Explanation object

```json
{
  "graphlet_id": "...",
  "risk_summary": "This graphlet shows rapid fan-out followed by consolidation near a known illicit transaction neighborhood.",
  "why_interesting": [
    "The graphlet is within two hops of labeled illicit activity.",
    "The address-to-transaction structure resembles layering.",
    "The graphlet embedding is close to prior illicit subgraphs."
  ],
  "matched_patterns": [
    {
      "pattern_id": "fanout_layering_001",
      "confidence": 0.78,
      "supporting_edges": ["e1", "e2", "e3"]
    }
  ],
  "model_scores": {
    "hetero_gnn_score": 0.84,
    "subgraph_similarity_score": 0.79,
    "rule_score": 0.72
  },
  "retrieved_evidence": [
    {
      "source": "Elliptic2 paper",
      "role": "supports subgraph AML framing"
    },
    {
      "source": "AML typology corpus",
      "role": "supports layering / structuring explanation"
    }
  ],
  "recommended_action": "Escalate for analyst review; inspect upstream source and downstream cash-out path."
}
```

---

# 15. Visualization framework

## 15.1 Do not use graph hairballs

Avoid showing the entire Bitcoin graph. Use scoped graphlets and impact views.

## 15.2 Four-panel visualization

| Panel                | Content                                                       |
| -------------------- | ------------------------------------------------------------- |
| **Temporal flow**    | Transaction/address behavior by time step                     |
| **Graphlet view**    | Local suspicious subgraph                                     |
| **Risk explanation** | Pattern, model score, supporting evidence                     |
| **Impact funnel**    | Raw flows → graphlets → suspicious graphlets → alerts → cases |

## 15.3 Example impact funnel

```text
1.2M address interactions
→ 180k candidate temporal graphlets
→ 14k structurally unusual graphlets
→ 1,200 high-risk AML pattern matches
→ 85 analyst-priority cases
```

## 15.4 Example visual graphlet

```text
Known illicit tx
      │
      ▼
 Address A
   ├── Tx1 ──► Address B
   ├── Tx2 ──► Address C
   ├── Tx3 ──► Address D
   └── Tx4 ──► Address E
                  │
                  ▼
             Exchange deposit
```

---

# 16. Caveats and risk controls

## 16.1 Original Elliptic caveats

| Caveat                     | Control                                                       |
| -------------------------- | ------------------------------------------------------------- |
| Feature opacity            | Do not claim operational deployability from original features |
| Possible split leakage     | Use temporal and graph-isolated splits                        |
| Transaction-only structure | Use Elliptic++ for heterogeneity                              |
| Coarse labels              | Use GraphRAG typology labels as explanatory overlays          |
| Unknown labels dominate    | Treat unknown as unlabeled, not benign                        |
| Dataset is old             | Position as benchmark/demo, not current threat intelligence   |

## 16.2 Elliptic++ caveats

| Caveat                                                | Control                                            |
| ----------------------------------------------------- | -------------------------------------------------- |
| More complex multi-view graph                         | Normalize into a single AML ontology               |
| Wallet/entity semantics can be inferred/probabilistic | Store cluster confidence and provenance            |
| Still limited natural-language data                   | Build external AML corpus                          |
| Class imbalance remains                               | Use precision/recall, PR-AUC, alert burden metrics |

## 16.3 Elliptic2 caveats

| Caveat                                    | Control                                                |
| ----------------------------------------- | ------------------------------------------------------ |
| Very large background graph               | Start with released labeled subgraphs                  |
| More complex preprocessing                | Use official scripts first                             |
| Subgraph models may differ from GraphSAGE | Treat GraphSAGE as one encoder, not the whole solution |
| Kaggle download/API friction              | Build resumable downloader                             |
| Need careful evaluation                   | Use held-out temporal/subgraph splits                  |

---

# 17. Recommended MVP sequence

## Phase 1 — Original Elliptic baseline

```text
1. Download Kaggle Elliptic.
2. Ingest transactions, edges, labels, features.
3. Build Bronze/Silver tables.
4. Train classical baseline and GNN baseline.
5. Visualize precision/recall and alert burden.
```

## Phase 2 — Elliptic++ heterogeneous graph

```text
1. Clone Elliptic++ GitHub repository.
2. Download linked Google Drive dataset.
3. Ingest transactions dataset and actors dataset.
4. Normalize address, transaction, actor, and interaction tables.
5. Build heterogeneous graphlets.
6. Run hetero GraphSAGE / relation-aware GNN.
7. Store graphlets in Arango.
```

## Phase 3 — GraphRAG explanation corpus

```text
1. Ingest Elliptic papers and README docs.
2. Ingest AML typology reports.
3. Ingest FinCEN/FATF/OFAC virtual-asset guidance.
4. Chunk and embed documents.
5. Link graphlet patterns to evidence chunks.
```

## Phase 4 — Elliptic2 subgraph demo

```text
1. Download Elliptic2 from Kaggle / official source.
2. Clone MITIBMxGraph/Elliptic2.
3. Run official preprocessing.
4. Materialize subgraphs as Gold graphlets.
5. Train / test subgraph embedding models.
6. Compare graphlet scores to deterministic AML patterns.
```

## Phase 5 — Unified AML demo

```text
1. Use Elliptic++ as streaming hetero graph substrate.
2. Use Elliptic2 as graphlet/subgraph learning benchmark.
3. Use GraphRAG to explain graphlet risk.
4. Use Arango for visual graph exploration.
5. Use Databricks for governed ingestion, CDF, model inference, and lineage.
```

---

# 18. Agent-ready task prompt

```text
Objective:
Build a downloader, ingestion, graphlet-construction, and explanation-preparation pipeline for the Elliptic Bitcoin dataset family: original Elliptic, Elliptic++, and Elliptic2.

Primary sources:
- Original Elliptic Kaggle dataset:
  https://www.kaggle.com/datasets/ellipticco/elliptic-data-set

- Original Elliptic release article:
  https://www.elliptic.co/blog/elliptic-dataset-cryptocurrency-financial-crime

- Original Elliptic paper:
  https://arxiv.org/abs/1908.02591

- Elliptic++ paper:
  https://arxiv.org/abs/2306.06108

- Elliptic++ GitHub repository:
  https://github.com/git-disl/EllipticPlusPlus

- Elliptic2 Kaggle dataset:
  https://www.kaggle.com/datasets/ellipticco/elliptic2-data-set

- Elliptic2 paper:
  https://arxiv.org/abs/2404.19109

- Elliptic2 GitHub repository:
  https://github.com/MITIBMxGraph/Elliptic2

- PyTorch Geometric Elliptic loader:
  https://pytorch-geometric.readthedocs.io/en/2.5.0/generated/torch_geometric.datasets.EllipticBitcoinDataset.html

Tasks:
1. Download all dataset files from Kaggle, GitHub, and Google Drive where applicable.
2. Preserve source directory hierarchy and file lineage.
3. Build file manifests with size, checksum, source URL, parse strategy, and semantic role.
4. Parse original Elliptic into transaction nodes, payment-flow edges, labels, time steps, and features.
5. Parse Elliptic++ into transactions, addresses, actor/entity data, address-address interactions, and address-transaction-address relations.
6. Parse Elliptic2 into background nodes, background edges, connected components, labeled subgraph nodes, and labeled subgraph edges.
7. Normalize all datasets into a common AML ontology with nodes such as Transaction, Address, EntityCluster, Flow, TimeStep, Graphlet, AMLPattern, EvidenceDocument, and Alert.
8. Materialize temporal graphlets using k-hop neighborhoods, time windows, actor neighborhoods, fan-in/fan-out motifs, and Elliptic2 labeled subgraphs.
9. Build Databricks Bronze/Silver/Gold schemas.
10. Build ArangoDB vertex and edge collection definitions.
11. Generate initial deterministic AML graph patterns: peel chain, fan-out layering, fan-in consolidation, illicit-proximity cash-out, and unknown actor resembling known illicit graphlets.
12. Ingest supporting natural-language documents: Elliptic papers, dataset READMEs, AML typologies, FATF virtual asset guidance, FinCEN advisories, OFAC sanctions guidance, and public crypto-crime reports.
13. Create GraphRAG explanation objects that link graphlet structure, model scores, nearest illicit examples, and supporting document chunks.
14. Output a reproducible ingestion report, schema report, graphlet report, and explanation-corpus report.
```

---

# 19. Final assessment

For your purposes:

| Choice                    | Recommendation                                                                            |
| ------------------------- | ----------------------------------------------------------------------------------------- |
| **Original Elliptic**     | Use as baseline only                                                                      |
| **Elliptic++**            | Use as the first real AML heterogeneous graph demo                                        |
| **Elliptic2**             | Use as the flagship graphlet/subgraph AML demo                                            |
| **GraphRAG requirement**  | Must be externally augmented with AML / crypto-forensics corpus                           |
| **Best Databricks story** | Bronze blockchain records → Silver AML ontology → Gold graphlets/scores/explanations      |
| **Best Arango story**     | Live semantic graph of addresses, transactions, actors, graphlets, patterns, and evidence |
| **Best visualization**    | Graphlet + timeline + evidence + impact funnel                                            |

My concrete recommendation: **start with Elliptic++**, because it gives you heterogeneous structure without Elliptic2’s full scale burden. Then use **Elliptic2** to validate the stronger “money laundering has a shape” thesis once the graphlet pipeline is stable.

[1]: https://pytorch-geometric.readthedocs.io/en/2.5.0/generated/torch_geometric.datasets.EllipticBitcoinDataset.html "torch_geometric.datasets.EllipticBitcoinDataset — pytorch_geometric  documentation"
[2]: https://www.elliptic.co/blog/elliptic-dataset-cryptocurrency-financial-crime "The Elliptic Data Set: Working With the Community to Combat Financial Crime in Cryptocurrencies"
[3]: https://arxiv.org/abs/2306.06108?utm_source=chatgpt.com "Demystifying Fraudulent Transactions and Illicit Nodes in the Bitcoin Network for Financial Forensics"
[4]: https://github.com/git-disl/EllipticPlusPlus "GitHub - git-disl/EllipticPlusPlus: Elliptic++ Dataset: A Graph Network of Bitcoin Blockchain Transactions and Wallet Addresses · GitHub"
[5]: https://www.kaggle.com/datasets/ellipticco/elliptic2-data-set?utm_source=chatgpt.com "Elliptic2"
[6]: https://arxiv.org/abs/2404.19109 "[2404.19109] The Shape of Money Laundering: Subgraph Representation Learning on the Blockchain with the Elliptic2 Dataset"
[7]: https://github.com/MITIBMxGraph/Elliptic2 "GitHub - MITIBMxGraph/Elliptic2: Official guide of using the Elliptic2 dataset introduced by the paper \"The Shape of Money Laundering: Subgraph Representation Learning on the Blockchain with the Elliptic2 Dataset\" · GitHub"
[8]: https://dfrws.org/presentation/the-enemy-of-reproducibility-is-opacity-whats-inside-the-elliptic-bitcoin-dataset-and-why-it-is-wrong/ "The Enemy of Reproducibility is Opacity: What's Inside the Elliptic Bitcoin Dataset (and Why It Is Wrong) - DFRWS"
