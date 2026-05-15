# DARPA Transparent Computing — Detailed Dataset + Documentation Brief

## 1. Executive summary

DARPA **Transparent Computing (TC)** is a cyber provenance program intended to make otherwise opaque computing systems observable by recording component interactions, causal dependencies, and end-to-end system behaviors. The program objective is directly aligned with your desired demo: **temporal event recognition over heterogeneous graphlets**, with **GraphRAG-backed explanations** grounded in adversary behavior, ground-truth reports, provenance schemas, and detection doctrine. DARPA describes TC as a system for recording provenance of system elements, dynamically tracking interactions and causal dependencies, assembling them into behaviors, and reasoning over those behaviors both forensically and in real time. ([darpa.mil][1])

The most relevant public release is **Transparent Computing Engagement 5**, hosted through the DARPA GitHub manifest and an external Google Drive folder. Engagement 5 contains event logs, ground truth, Avro schema material, CDM documentation, Java parsing tooling, and data streams from multiple TA1 tagging/tracking performers: **cadets, clearscope, fivedirections, marple, theia, and trace**. ([GitHub][2])

For your use case, the right positioning is:

> **Databricks materializes streaming provenance events into typed temporal graphlets; a heterogeneous GNN scores graphlet structure; Arango stores the semantic provenance graph; GraphRAG uses DARPA ground truth, CDM docs, MITRE ATT&CK, and detection-rule corpora to explain and generate event patterns.**

---

# 2. Core DARPA TC purpose

DARPA frames the problem as follows:

Modern computing systems often behave like black boxes: they accept inputs and generate outputs, but they expose little internal visibility. This impedes detection of advanced persistent threats because individual adversary actions can look legitimate in isolation while becoming malicious when connected across time, hosts, processes, files, sockets, users, and network flows. DARPA’s goal was to provide **high-fidelity visibility into component interactions** across layers of software abstraction while maintaining low overhead. ([darpa.mil][1])

The TC program aimed to develop technologies that:

| Capability                             | Meaning for your demo                                                                                 |
| -------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Record provenance of system components | Capture process, file, socket, module, and data-object activity                                       |
| Track causal dependencies              | Build directed relations such as process-spawned-process, process-read-file, process-connected-socket |
| Assemble behaviors                     | Convert raw event streams into temporal causal chains                                                 |
| Reason in real time and forensically   | Support both streaming event recognition and post-hoc explanation                                     |
| Connect individually benign actions    | Detect compound behaviors that are suspicious only in aggregate                                       |
| Support policy enforcement             | Map graph patterns to allowed/blocked behavior at enterprise ingress/egress points                    |

DARPA explicitly says the program was intended to help detect APTs, support root-cause analysis, and perform damage assessment once adversary activity is identified. ([darpa.mil][1])

---

# 3. Primary source links

## 3.1 DARPA TC program page

**Purpose:** High-level DARPA program description.

**Use in your system:**
Use this as a foundational GraphRAG document that explains the strategic intent of provenance-based detection, APT visibility, causal dependency tracking, and real-time/forensic reasoning.

**Link:**
[https://www.darpa.mil/research/programs/transparent-computing](https://www.darpa.mil/research/programs/transparent-computing)

DARPA’s page is especially useful for explaining why graph-based causal reasoning matters: the program explicitly targets “connecting the dots” across activities that are individually legitimate but collectively malicious. ([darpa.mil][1])

---

## 3.2 DARPA Transparent Computing GitHub repository

**Purpose:** Official public manifest for TC Engagement 5 and Engagement 3.

**Use in your system:**
This should be your downloader agent’s starting manifest. The repo itself is not the full dataset; it points to the Google Drive release and describes the folder contents.

**Link:**
[https://github.com/darpa-i2o/transparent-computing](https://github.com/darpa-i2o/transparent-computing)

The README states that DARPA released the Engagement 5 files in the public domain to stimulate research, but also cautions that the data is released as-is, with no warranty as to correctness, accuracy, or usefulness. This matters for your framework: preserve uncertainty, provenance, and data-quality flags in the pipeline. ([GitHub][2])

---

## 3.3 Engagement 5 Google Drive folder

**Purpose:** Large-file storage for the actual Engagement 5 data.

**Use in your system:**
This is the primary payload source for the downloader. The GitHub manifest states that the dataset is hosted externally by Five Directions on Google Drive because of its size. ([GitHub][2])

**Link:**
[https://drive.google.com/drive/folders/1okt4AYElyBohW4XiOBqmsvjwXsnUjLVf](https://drive.google.com/drive/folders/1okt4AYElyBohW4XiOBqmsvjwXsnUjLVf)

**Important note:** I could verify the Google Drive link through the GitHub manifest, but browser access to the Drive folder itself may not reliably expose a complete file listing without a Drive-aware downloader or API client. Your agent should use one of:

```text
gdown
rclone
Google Drive API
manual browser-exported file manifest
```

---

## 3.4 Engagement 3 release

**Purpose:** Earlier TC release, useful for comparison and potentially easier startup.

**Use in your system:**
Engagement 3 may be useful as a smaller or older baseline dataset. It has similar artifacts: operational log, ground truth, Avro/CDM schema, parsing tools, and TA1 performer data. The README also identifies known-good topics, which may be useful if you want a cleaner first ingestion. ([GitHub][3])

**Link:**
[https://github.com/darpa-i2o/Transparent-Computing/blob/master/README-E3.md](https://github.com/darpa-i2o/Transparent-Computing/blob/master/README-E3.md)

---

## 3.5 TC Data Annotation Stack repository

**Purpose:** Third-party/derived annotation and visualization stack for Engagement 5.

**Use in your system:**
This repository is useful because it shows one practical way to ingest, visualize, and annotate TC E5 data with Elasticsearch, Logstash, and Grafana. It also includes a `drive_download.py`, schema folder, tools folder, ground-truth folder, and Engagement 5 event log file. ([GitHub][4])

**Link:**
[https://github.com/tanishqjasoria/darpa-tc-en5](https://github.com/tanishqjasoria/darpa-tc-en5)

The repository describes itself as a **Transparent Computing Data Annotation Stack** intended to help researchers visualize Engagement 5 attack data by coupling real system event data with the attack write-up from the organization administering the attacks. ([GitHub][4])

---

## 3.6 OpTC follow-on dataset

**Purpose:** Larger-scale operationally transparent cyber dataset derived from TC-style architecture.

**Use in your system:**
OpTC is not the same as TC E5, but it is relevant as a follow-on/scaled dataset. It includes endpoint telemetry from Windows 10 endpoints, Kafka-style streaming architecture, eCAR records, Bro/Zeek network data, red-team ground truth, and roughly a terabyte of compressed JSON-compatible data. ([GitHub][5])

**Link:**
[https://github.com/FiveDirections/OpTC-data](https://github.com/FiveDirections/OpTC-data)

OpTC is useful if you later want a larger, cleaner, JSON-oriented cyber-hunting dataset after proving the pipeline on TC E5.

---

# 4. Engagement 5 file manifest

The official E5 manifest identifies these major release components. ([GitHub][2])

| Path / file                                         | Type              | Purpose                                                    | Use in your architecture                                  |
| --------------------------------------------------- | ----------------- | ---------------------------------------------------------- | --------------------------------------------------------- |
| `operational_event_log.md`                          | Markdown timeline | Log of activity on the TC E5 test range                    | RAG chronology, attack/benign time alignment              |
| `ground truth/tc_ground_truth_report_e5_update.pdf` | PDF report        | TA5.1 ground truth and indicators of compromise            | Label source, explanation source, evaluation source       |
| `tools/ta5-java-consumer.tar.gz`                    | Java tooling      | Parses Avro binary files, emits JSON, runs semantic checks | Ingestion bootstrap or reference parser                   |
| `schema/TCCDMDatum.avsc`                            | Avro schema       | Machine-readable CDM schema                                | Spark/Avro ingestion schema                               |
| `schema/CDM20.avdl`                                 | Avro IDL          | Human-readable CDM schema with notes                       | Schema documentation for GraphRAG and ontology generation |
| `schema/cdm.pdf`                                    | PDF documentation | Human-readable explanation of CDM concepts                 | Core GraphRAG source and ontology design guide            |
| `data/cadets`                                       | Data folder       | TA1 performer telemetry                                    | One candidate primary stream                              |
| `data/clearscope`                                   | Data folder       | TA1 performer telemetry                                    | Cross-performer comparison                                |
| `data/fivedirections`                               | Data folder       | TA1 performer telemetry                                    | Cross-performer comparison                                |
| `data/marple`                                       | Data folder       | TA1 performer telemetry                                    | Cross-performer comparison                                |
| `data/theia`                                        | Data folder       | TA1 performer telemetry                                    | One candidate primary stream                              |
| `data/trace`                                        | Data folder       | TA1 performer telemetry                                    | Cross-performer comparison                                |

---

# 5. Program technical areas

The TC program split responsibilities into multiple technical areas. These are important because they explain which files are data, which files are ground truth, and which files are architecture/schema support.

| Technical Area                             | Role                                                                                                                              | Relevance                                                    |
| ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| **TA1 — Tagging and Tracking**             | Develop technologies that tag and track component interactions, such as parent/child process links and file accesses by processes | Source of the raw event streams                              |
| **TA2 — Detection and Policy Enforcement** | Construct causal graphs from TA1 events and reason over them in real time and forensics                                           | Your architecture effectively recreates/modernizes this role |
| **TA3 — Architecture**                     | Develop TC architecture, data interchange, and storage requirements                                                               | Source of schema, CDM, and annotations                       |
| **TA5.1 — Adversarial Challenge Team**     | Execute realistic APT-like attacks and provide ground truth / IOCs                                                                | Source of labels, attack narratives, and explanation anchors |

The E5 release includes TA1 data, TA3 annotations, and TA5.1 ground truth, but it does **not** include TA2 detection system internals. ([GitHub][2])

That gap is an opportunity: your Databricks + Arango + GraphRAG + GNN stack becomes the modern TA2-style reasoning layer.

---

# 6. Engagement 5 scenario structure

Engagement 5 occurred in **May 2019** and was the last of five planned TC engagement exercises. The scenario was structured as:

1. Multiple instantiations of each TA1 performer were deployed on separate host platforms.
2. The exercise began with benign data generation.
3. Scripted benign activity was run on each host, and performers knew those activities were being executed.
4. After benign generation, the TA5.1 adversarial team controlled the test range.
5. TA5.1 executed activities based on new and existing APT behaviors.
6. Benign background traffic continued during malicious activity.
7. Malicious actions were conducted roughly during weekday business hours, approximately 9 a.m. to 5 p.m., so TA2 performers could provide real-time alerts with reasonable staffing.
8. After the live engagement, TA2 performers were given time for forensic review and missed-detection analysis. ([GitHub][2])

This is excellent for your use case because it supports both:

| Mode           | Dataset use                                                             |
| -------------- | ----------------------------------------------------------------------- |
| Streaming mode | Replay events chronologically through Databricks                        |
| Forensic mode  | Use ground truth and event logs to explain attack chains after the fact |

---

# 7. Why TC E5 is a strong fit for your architecture

## 7.1 Temporal streaming

TC event records can be replayed in timestamp order. This gives you a natural simulated stream:

```text
compressed Avro / CDM records
→ Bronze raw event stream
→ Silver typed events/entities/relations
→ Gold temporal graphlets
→ graphlet scoring
→ event recognition
→ analyst explanation
```

The E5 setup explicitly includes benign periods followed by red-team activity while benign background traffic continues. That supports realistic detection workflows where the system must distinguish malicious causal chains from normal operational noise. ([GitHub][2])

---

## 7.2 Heterogeneous graph structure

The TC problem is inherently heterogeneous. The entities are not only “nodes”; they are typed operational objects:

| Entity type               | Example semantic role                   |
| ------------------------- | --------------------------------------- |
| Process / subject         | Active execution context                |
| File                      | Persistent data object                  |
| Socket / network endpoint | Communication object                    |
| Host                      | Execution environment                   |
| User / principal          | Identity context                        |
| Event                     | Time-stamped interaction                |
| Artifact                  | Program, script, binary, temporary file |
| Attack stage              | Ground-truth or inferred behavior unit  |
| IOC                       | Indicator attached to ground truth      |

Typical relations:

| Relation            | Meaning                                  |
| ------------------- | ---------------------------------------- |
| `SPAWNED`           | Process created child process            |
| `EXECUTED`          | Process executed binary/command          |
| `READ`              | Process read file/object                 |
| `WROTE`             | Process wrote file/object                |
| `CONNECTED_TO`      | Process/socket connected to endpoint     |
| `SENT_TO`           | Data emitted to network object           |
| `RECEIVED_FROM`     | Data received from network object        |
| `RAN_ON`            | Process executed on host                 |
| `ACTED_AS`          | Process/user identity association        |
| `PART_OF_GRAPHLET`  | Entity belongs to accumulated graphlet   |
| `MATCHES_TECHNIQUE` | Graphlet matched ATT&CK technique        |
| `SUPPORTED_BY`      | Explanation supported by source document |

This maps cleanly to **PyTorch Geometric `HeteroData`**, ArangoDB multi-collection graphs, and ontology-driven GraphRAG.

---

## 7.3 Rich natural-language support

TC E5 has unusually strong documentation support compared with many cyber datasets:

| Document type             | Why it matters                                       |
| ------------------------- | ---------------------------------------------------- |
| DARPA program description | Explains high-level mission and provenance rationale |
| E5 README                 | Explains release structure, TAs, scenario, caveats   |
| Operational event log     | Timeline grounding                                   |
| Ground-truth PDF          | Attack actions, IOCs, evaluation guidance            |
| CDM schema docs           | Data-model semantics                                 |
| TA5.1 attack description  | Narrative adversary behavior                         |
| MITRE ATT&CK              | Technique/tactic grounding                           |
| Detection-rule corpora    | Practical pattern-generation support                 |
| Provenance IDS papers     | Algorithmic context and pitfalls                     |

MITRE ATT&CK is especially important because it is a globally accessible knowledge base of adversary tactics and techniques based on real-world observations. ([MITRE ATT&CK][6]) ATT&CK data components also provide a way to define the observable properties relevant to detecting techniques. ([MITRE ATT&CK][7])

---

# 8. Recommended document corpus for GraphRAG

## 8.1 Tier 1 — Mandatory corpus

These should be ingested before any model-driven pattern generation.

| Source                   | Role                         | Link                                                                                                                           |
| ------------------------ | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| DARPA TC program page    | Strategic rationale          | [https://www.darpa.mil/research/programs/transparent-computing](https://www.darpa.mil/research/programs/transparent-computing) |
| E5 README                | Release manifest and caveats | [https://github.com/darpa-i2o/transparent-computing](https://github.com/darpa-i2o/transparent-computing)                       |
| E5 operational event log | Timeline grounding           | In E5 Drive / manifest                                                                                                         |
| E5 ground-truth report   | Attack labels and IOCs       | In E5 Drive / manifest                                                                                                         |
| `TCCDMDatum.avsc`        | Machine schema               | In E5 Drive / schema                                                                                                           |
| `CDM20.avdl`             | Human-readable schema        | In E5 Drive / schema                                                                                                           |
| `cdm.pdf`                | CDM concept explanation      | In E5 Drive / schema                                                                                                           |

---

## 8.2 Tier 2 — Detection and explanation corpus

| Source                                                 | Role                                              | Link                                                                                               |
| ------------------------------------------------------ | ------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| MITRE ATT&CK Enterprise Matrix                         | Tactic/technique taxonomy                         | [https://attack.mitre.org/](https://attack.mitre.org/)                                             |
| MITRE ATT&CK Data Sources                              | Maps telemetry categories to adversary techniques | [https://attack.mitre.org/datasources/](https://attack.mitre.org/datasources/)                     |
| MITRE ATT&CK Data Components                           | Fine-grained observable components                | [https://attack.mitre.org/datacomponents/](https://attack.mitre.org/datacomponents/)               |
| Network Connection Creation component                  | Useful for C2, lateral movement, exfil graphlets  | [https://attack.mitre.org/datacomponents/DC0082/](https://attack.mitre.org/datacomponents/DC0082/) |
| Technique T1543 — Create or Modify System Process      | Persistence / privilege escalation example        | [https://attack.mitre.org/techniques/T1543/](https://attack.mitre.org/techniques/T1543/)           |
| Technique T1049 — System Network Connections Discovery | Discovery graphlet example                        | [https://attack.mitre.org/techniques/T1049/](https://attack.mitre.org/techniques/T1049/)           |
| Technique T1565 — Data Manipulation                    | Integrity-impact graphlet example                 | [https://attack.mitre.org/techniques/T1565/](https://attack.mitre.org/techniques/T1565/)           |

---

## 8.3 Tier 3 — Research context corpus

| Source                                                        | Role                                                       | Link                                                                                                                             |
| ------------------------------------------------------------- | ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Event-based Data Model for Granular Information Flow Tracking | Explains CDM rationale and provenance model                | [https://www.usenix.org/system/files/tapp2020-paper-khoury.pdf](https://www.usenix.org/system/files/tapp2020-paper-khoury.pdf)   |
| Provenance-based IDS survey                                   | Broader provenance IDS landscape                           | [https://dl.acm.org/doi/fullHtml/10.1145/3539605](https://dl.acm.org/doi/fullHtml/10.1145/3539605)                               |
| Reproducibility of provenance IDS                             | Evaluation pitfalls, missing scripts, ground-truth caveats | [https://www.csl.sri.com/users/gehani/papers/REP-2025.PIDDL.pdf](https://www.csl.sri.com/users/gehani/papers/REP-2025.PIDDL.pdf) |
| KAIROS paper                                                  | Whole-system provenance investigation approach             | [https://tfjmp.org/publications/2024-sp-supp.pdf](https://tfjmp.org/publications/2024-sp-supp.pdf)                               |
| OpTC repository                                               | Larger follow-on dataset and eCAR model                    | [https://github.com/FiveDirections/OpTC-data](https://github.com/FiveDirections/OpTC-data)                                       |

The CDM research paper is especially relevant because it states that the model was developed for attack provenance analysis under DARPA TC and was intended to represent causal events across multiple platforms and granularities. ([USENIX][8])

---

# 9. Downloader-agent requirements

## 9.1 Agent objective

The downloader agent should:

```text
1. Clone or fetch the DARPA TC GitHub manifest.
2. Resolve the E5 Google Drive folder.
3. Enumerate all folders and files.
4. Download schema, tools, documentation, ground truth, and data.
5. Preserve original directory hierarchy.
6. Compute checksums.
7. Record metadata into a local manifest.
8. Optionally convert compressed Avro/CDM data into JSON or Delta-compatible records.
9. Emit a machine-readable ingestion plan for Databricks.
```

---

## 9.2 Preferred local directory layout

```text
darpa_tc/
  sources/
    github/
      README.md
      README-E3.md
    drive/
      raw_manifest.json
      downloaded_files_manifest.json

  docs/
    program/
      darpa_tc_program_page.md
    e5/
      operational_event_log.md
      tc_ground_truth_report_e5_update.pdf
      cdm.pdf
      CDM20.avdl
    e3/
      README-E3.md
      tc_ground_truth_report_e3_update.pdf

  schema/
    TCCDMDatum.avsc
    CDM20.avdl

  tools/
    ta5-java-consumer.tar.gz
    extracted/
      ...

  data/
    e5/
      cadets/
      clearscope/
      fivedirections/
      marple/
      theia/
      trace/

  derived/
    json/
    delta/
    parquet/
    graphlets/
    embeddings/

  manifests/
    files.csv
    files.json
    checksums.sha256
    ingestion_status.json
```

---

## 9.3 Downloader implementation options

| Tool                             | Pros                                                  | Cons                                                 |
| -------------------------------- | ----------------------------------------------------- | ---------------------------------------------------- |
| `gdown`                          | Simple for public Google Drive folders/files          | May struggle with very large folders or quota limits |
| `rclone`                         | Strong for Drive folder syncs and resumable downloads | Requires config/token setup                          |
| Google Drive API                 | Most robust and auditable                             | Requires API credentials                             |
| Manual manifest + `wget`/browser | Simple fallback                                       | Not scalable                                         |

For an LLM agent, I would define a strategy cascade:

```text
Attempt 1: rclone sync public Drive folder
Attempt 2: Google Drive API enumerate + download
Attempt 3: gdown folder download
Attempt 4: ask user for exported Drive manifest or local folder mount
```

---

## 9.4 Metadata the downloader should capture

For each file:

```json
{
  "source_dataset": "DARPA Transparent Computing Engagement 5",
  "source_url": "https://drive.google.com/drive/folders/1okt4AYElyBohW4XiOBqmsvjwXsnUjLVf",
  "relative_path": "data/cadets/...",
  "file_name": "...",
  "file_type": "bin.gz | avsc | avdl | pdf | md | tar.gz",
  "size_bytes": 0,
  "sha256": "...",
  "download_time_utc": "...",
  "modified_time_source": "...",
  "status": "downloaded | skipped | failed | parsed",
  "parse_strategy": "avro_cdm | pdf_text | markdown | archive_extract",
  "notes": ""
}
```

---

# 10. Ingestion framework

## 10.1 Bronze layer

Bronze should preserve rawness and lineage.

```text
bronze_tc_raw_file_manifest
bronze_tc_raw_cdm_records
bronze_tc_raw_json_records
bronze_tc_raw_docs
bronze_tc_raw_ground_truth
bronze_tc_raw_operational_log
```

### Bronze principles

| Principle                    | Requirement                                                              |
| ---------------------------- | ------------------------------------------------------------------------ |
| Preserve raw records         | Do not discard unknown fields                                            |
| Preserve source file lineage | Every record stores source file, byte offset if possible, parser version |
| Preserve original timestamps | Do not normalize away source event time                                  |
| Capture parser errors        | Malformed records become error rows, not silent drops                    |
| Keep performer identity      | `cadets`, `theia`, etc. must remain first-class fields                   |
| Keep engagement identity     | `E5` and `E3` remain separate                                            |

---

## 10.2 Silver layer

Silver normalizes CDM records into semantic entities and relations.

Recommended tables:

```text
silver_tc_event
silver_tc_subject
silver_tc_process
silver_tc_file_object
silver_tc_netflow_object
silver_tc_socket
silver_tc_principal
silver_tc_host
silver_tc_relation
silver_tc_artifact
silver_tc_ground_truth_event
silver_tc_ioc
silver_tc_time_window
```

### Example normalized event record

```json
{
  "event_id": "uuid-or-source-id",
  "event_type": "READ | WRITE | EXECUTE | CONNECT | SEND | RECV | FORK | CLONE",
  "event_time": "2019-05-xxT...",
  "performer": "cadets",
  "host_id": "...",
  "subject_id": "...",
  "source_entity_id": "...",
  "target_entity_id": "...",
  "source_entity_type": "process",
  "target_entity_type": "file",
  "direction": "subject_to_object",
  "source_file": "...",
  "raw_record_hash": "..."
}
```

---

## 10.3 Gold layer

Gold should materialize graphlets and explanations.

```text
gold_tc_graphlet
gold_tc_graphlet_node
gold_tc_graphlet_edge
gold_tc_graphlet_feature
gold_tc_graphlet_embedding
gold_tc_graphlet_score
gold_tc_pattern_match
gold_tc_attack_stage_alignment
gold_tc_explanation
gold_tc_alert
```

### Recommended graphlet accumulation triggers

| Trigger                                   | Graphlet type                   |
| ----------------------------------------- | ------------------------------- |
| Process spawn                             | Process lineage graphlet        |
| File write after suspicious read chain    | File staging graphlet           |
| Outbound connection after file access     | Exfiltration candidate graphlet |
| Rare process-parent relation              | Execution anomaly graphlet      |
| Many files read then archive/socket write | Collection/exfil graphlet       |
| Network connection discovery command      | Discovery graphlet              |
| Cross-host flow                           | Lateral movement candidate      |
| Known IOC observed                        | Ground-truth anchored graphlet  |

---

# 11. Heterogeneous graph schema

## 11.1 Node collections

For ArangoDB or equivalent KG:

```text
Host
Principal
Subject
Process
File
Socket
NetFlow
MemoryObject
Artifact
Command
Event
Graphlet
AttackStage
Technique
Tactic
Indicator
EvidenceDocument
EvidenceChunk
ModelRun
Alert
```

## 11.2 Edge collections

```text
RAN_ON
ACTED_AS
SPAWNED
EXECUTED
READ
WROTE
DELETED
RENAMED
OPENED
CONNECTED_TO
SENT_TO
RECEIVED_FROM
RESOLVED_TO
MODIFIED
CONTAINS_EVENT
CONTAINS_ENTITY
DERIVED_FROM_FILE
MATCHES_PATTERN
MATCHES_TECHNIQUE
ALIGNED_WITH_GROUND_TRUTH
SUPPORTED_BY_CHUNK
SCORED_BY_MODEL
GENERATED_ALERT
```

## 11.3 Event-to-edge rule

Treat low-level CDM events as both:

1. **event nodes** for auditability, and
2. **typed semantic edges** for graph analytics.

Example:

```text
Event E123:
  type = EVENT_READ
  subject = process:P1
  object = file:F9
  timestamp = T

Graph representation:
  process:P1 -[:READ {event_id:E123, timestamp:T}]-> file:F9
  event:E123 -[:HAS_SUBJECT]-> process:P1
  event:E123 -[:HAS_OBJECT]-> file:F9
```

This gives you both fast graph traversal and high-fidelity provenance.

---

# 12. GraphRAG explanation framework

## 12.1 Explanation pipeline

```text
graphlet detected
→ retrieve graphlet structural summary
→ retrieve matching ground-truth interval, if any
→ retrieve relevant CDM schema docs
→ retrieve ATT&CK techniques/data components
→ retrieve similar known detection rules
→ generate explanation
→ attach evidence chunks
→ store explanation in Gold + Arango
```

## 12.2 Explanation object

```json
{
  "graphlet_id": "...",
  "alert_id": "...",
  "summary": "A process read multiple files, wrote a staged artifact, and initiated outbound network communication.",
  "why_interesting": [
    "The causal chain links file access to network egress.",
    "The process lineage is uncommon for this host.",
    "The sequence aligns with collection/exfiltration behavior."
  ],
  "matched_patterns": [
    {
      "pattern_id": "exfil_candidate_001",
      "confidence": 0.82,
      "evidence_edges": ["e1", "e2", "e3"]
    }
  ],
  "attack_mapping": [
    {
      "framework": "MITRE ATT&CK",
      "technique_id": "candidate",
      "technique_name": "exfiltration or C2-related behavior",
      "supporting_docs": ["..."]
    }
  ],
  "ground_truth_alignment": {
    "status": "matched | near_miss | unknown | benign",
    "ground_truth_event_id": "..."
  },
  "model_scores": {
    "hetero_gnn_score": 0.91,
    "novelty_score": 0.73,
    "rule_score": 0.88
  },
  "evidence_chunks": [
    {
      "doc_id": "cdm.pdf",
      "chunk_id": "...",
      "quote_or_summary": "CDM relation semantics..."
    },
    {
      "doc_id": "tc_ground_truth_report_e5_update.pdf",
      "chunk_id": "...",
      "quote_or_summary": "Ground truth activity..."
    }
  ]
}
```

---

# 13. Pattern-generation framework

## 13.1 Human-authored seed patterns

Start with deterministic graph patterns before adding LLM-generated patterns.

### Pattern 1 — Process lineage anomaly

```text
Process A
  -[:SPAWNED]-> Process B
where
  B.command is rare for A
  OR B.path is unusual
  OR B.user privilege differs from A
```

### Pattern 2 — File staging before egress

```text
Process P
  -[:READ]-> File F1
  -[:READ]-> File F2
  -[:WROTE]-> File Archive
  -[:CONNECTED_TO]-> Socket S
  -[:SENT_TO]-> RemoteEndpoint R
within time window W
```

### Pattern 3 — Discovery command followed by connection

```text
Process P
  -[:EXECUTED]-> Command C
  -[:CONNECTED_TO]-> RemoteEndpoint R
where
  C resembles network/process/system discovery
```

### Pattern 4 — Persistence-like service modification

```text
Process P
  -[:WROTE|MODIFIED]-> SystemServiceFile
  -[:SPAWNED]-> LongRunningProcess
```

This aligns with ATT&CK persistence concepts such as creating or modifying system-level processes. ([MITRE ATT&CK][9])

---

## 13.2 LLM-generated graph pattern workflow

The LLM agent should not directly register arbitrary standing queries. It should produce a proposed pattern artifact:

```json
{
  "candidate_pattern_id": "generated_exfil_004",
  "natural_language_description": "Detect a process that reads sensitive files and then initiates outbound communication.",
  "required_node_types": ["Process", "File", "Socket", "RemoteEndpoint"],
  "required_edge_types": ["READ", "CONNECTED_TO", "SENT_TO"],
  "temporal_constraints": [
    "READ occurs before CONNECTED_TO",
    "All events occur within 10 minutes"
  ],
  "negative_constraints": [
    "Ignore known package manager processes",
    "Ignore known backup service processes"
  ],
  "source_documents": [
    "MITRE ATT&CK data component DC0082",
    "DARPA CDM documentation",
    "E5 ground truth"
  ],
  "query_target": "Arango AQL | Databricks SQL | GraphFrames | PyG prefilter",
  "validation_status": "draft"
}
```

Then use a policy gate:

```text
LLM candidate pattern
→ schema validation
→ test on known benign slice
→ test on ground-truth attack interval
→ analyst review
→ register as standing query
```

---

# 14. GNN / GraphSAGE design

## 14.1 Unit of inference

The primary unit should be the **temporal graphlet**, not just the individual event.

Recommended graphlet types:

| Graphlet                  | Anchor                           |
| ------------------------- | -------------------------------- |
| Process lineage graphlet  | Process spawn / fork / exec      |
| File interaction graphlet | File read/write/delete/rename    |
| Network egress graphlet   | Socket connect/send              |
| Cross-host graphlet       | Network relation crossing hosts  |
| IOC-anchored graphlet     | Ground-truth IOC hit             |
| ATT&CK candidate graphlet | Rule-matched suspicious sequence |
| Sliding window graphlet   | Fixed time/entity window         |

## 14.2 Heterogeneous GNN

Use PyTorch Geometric `HeteroData` or an equivalent hetero-graph representation.

Node types:

```text
process
file
socket
host
principal
event
command
graphlet
```

Edge types:

```text
(process, spawned, process)
(process, read, file)
(process, wrote, file)
(process, connected_to, socket)
(socket, sent_to, remote_endpoint)
(process, ran_on, host)
(principal, executed_as, process)
(graphlet, contains, event)
(graphlet, contains, process)
(graphlet, contains, file)
```

## 14.3 Feature classes

| Feature class          | Examples                                                        |
| ---------------------- | --------------------------------------------------------------- |
| Structural             | degree, fan-in/fan-out, path length, motif counts               |
| Temporal               | inter-event gaps, burstiness, ordering                          |
| Entity rarity          | rare parent/child process, rare file path, rare remote endpoint |
| Behavioral             | read-before-send, write-before-exec, spawn-before-connect       |
| Ground-truth proximity | within known attack interval, shares IOC                        |
| Text-derived           | ATT&CK technique embedding, command-line semantic embedding     |
| Performer-specific     | cadets/theia/etc. source indicator                              |

---

# 15. Databricks architecture

## 15.1 Tables

```text
catalog.cyber_bronze.tc_raw_files
catalog.cyber_bronze.tc_raw_records
catalog.cyber_bronze.tc_raw_docs

catalog.cyber_silver.tc_events
catalog.cyber_silver.tc_entities
catalog.cyber_silver.tc_edges
catalog.cyber_silver.tc_ground_truth
catalog.cyber_silver.tc_doc_chunks

catalog.cyber_gold.tc_graphlets
catalog.cyber_gold.tc_graphlet_nodes
catalog.cyber_gold.tc_graphlet_edges
catalog.cyber_gold.tc_embeddings
catalog.cyber_gold.tc_pattern_matches
catalog.cyber_gold.tc_explanations
catalog.cyber_gold.tc_alerts
```

## 15.2 Services / jobs

| Component                 | Function                                                     |
| ------------------------- | ------------------------------------------------------------ |
| `tc-downloader`           | Pulls Drive/GitHub files                                     |
| `tc-avro-parser`          | Converts compressed Avro/CDM records                         |
| `tc-doc-ingestor`         | Chunks PDFs/Markdown/schema docs                             |
| `tc-normalizer`           | Converts raw CDM records into typed event/entity/edge tables |
| `tc-graphlet-accumulator` | Maintains rolling graphlets                                  |
| `tc-hetero-gnn-worker`    | Runs GraphSAGE / hetero-GNN inference                        |
| `tc-arango-sync`          | Upserts graphlets/entities/edges into Arango                 |
| `tc-graphrag-explainer`   | Generates evidence-backed explanations                       |
| `tc-pattern-registrar`    | Validates and registers standing graph queries               |

---

# 16. Visualization framework

Use four synchronized panels.

## 16.1 Temporal swimlane

Rows:

```text
Host
User
Process
File
Socket
Remote endpoint
Ground truth
Alert
```

Shows:

```text
event sequence
attack windows
graphlet boundaries
pattern triggers
model-score changes
```

## 16.2 Graphlet panel

Shows the actual causal subgraph:

```text
User → Process → File
              ↘ Socket → Remote Endpoint
```

## 16.3 Evidence panel

Shows retrieved support:

```text
Ground truth activity
CDM schema explanation
ATT&CK technique/data component
similar historical graphlet
model feature contribution
```

## 16.4 Impact funnel

Example:

```text
500M raw CDM records
→ 80M typed provenance edges
→ 3.2M temporal graphlets
→ 18,000 anomalous graphlets
→ 420 ATT&CK-aligned pattern matches
→ 37 analyst-priority incidents
```

---

# 17. Caveats and risk controls

## 17.1 Dataset imperfections

DARPA explicitly states that the release is as-is and practically guaranteed to be imperfect because it was generated by research prototypes. ([GitHub][2])

Design implications:

| Risk                               | Control                                                          |
| ---------------------------------- | ---------------------------------------------------------------- |
| Missing records                    | Preserve parser errors and gap metrics                           |
| Inconsistent performer output      | Normalize into your own ontology                                 |
| Ground truth not perfectly aligned | Store confidence and alignment status                            |
| Fictional IP/domain names          | Treat network identifiers as scenario-local                      |
| Large compressed files             | Use resumable downloader and incremental parser                  |
| Avro schema complexity             | Start with Java consumer or Spark Avro                           |
| Overclaiming ML performance        | Emphasize explainable event recognition, not benchmark supremacy |

---

## 17.2 Evaluation pitfalls

Recent reproducibility work on provenance-based IDS warns that evaluations can suffer from missing scripts, missing thresholds, hardcoded file names, and ground-truth handling issues. ([csl.sri.com][10])

For your demo, avoid claiming “state-of-the-art detection.” Instead claim:

```text
The system demonstrates a governed event-recognition pipeline that materializes,
scores, explains, and visualizes temporal provenance graphlets using public
DARPA TC telemetry and documentation.
```

---

# 18. Recommended MVP sequence

## Phase 1 — Download and inventory

```text
1. Clone GitHub manifest.
2. Download E5 Drive folder.
3. Build file manifest.
4. Extract schema/tools/docs.
5. Verify Avro/CDM parser path.
```

## Phase 2 — Documentation GraphRAG

```text
1. Ingest README, CDM docs, ground truth, operational event log.
2. Add MITRE ATT&CK pages and data components.
3. Build document chunks and embeddings.
4. Create EvidenceDocument / EvidenceChunk graph in Arango.
```

## Phase 3 — One performer stream

Pick **CADETS** or **THEIA** first.

```text
1. Parse raw compressed records.
2. Normalize events/entities/edges.
3. Replay events chronologically.
4. Build process/file/socket graphlets.
```

## Phase 4 — Initial detection patterns

Implement deterministic patterns:

```text
process lineage anomaly
file staging before egress
discovery command followed by outbound connection
rare parent-child process relation
ground-truth IOC proximity
```

## Phase 5 — GNN embedding

```text
1. Build HeteroData graphlets.
2. Encode structural + temporal + semantic features.
3. Train or prototype unsupervised/weakly supervised graphlet embeddings.
4. Score novelty and similarity to known attack graphlets.
```

## Phase 6 — Explanation and visualization

```text
1. For each alert, retrieve supporting docs.
2. Generate graphlet summary.
3. Show timeline + graphlet + evidence + score.
4. Store explanation in Gold and Arango.
```

---

# 19. Agent-ready task prompt

You can give this to an LLM/data agent:

```text
Objective:
Build a downloader and explanation-preparation pipeline for the DARPA Transparent Computing Engagement 5 dataset.

Primary sources:
- DARPA TC program page: https://www.darpa.mil/research/programs/transparent-computing
- DARPA TC GitHub manifest: https://github.com/darpa-i2o/transparent-computing
- E5 Google Drive folder: https://drive.google.com/drive/folders/1okt4AYElyBohW4XiOBqmsvjwXsnUjLVf
- TC Data Annotation Stack: https://github.com/tanishqjasoria/darpa-tc-en5
- MITRE ATT&CK: https://attack.mitre.org/
- MITRE ATT&CK data sources: https://attack.mitre.org/datasources/
- MITRE ATT&CK data components: https://attack.mitre.org/datacomponents/

Tasks:
1. Download and preserve the full E5 folder hierarchy.
2. Extract schema, tools, ground truth, operational event log, and performer data.
3. Build a machine-readable file manifest with checksums, sizes, source URLs, file types, and parse strategy.
4. Parse or prepare parsing for compressed Avro/CDM files using the provided Java consumer, Spark Avro, or another schema-compliant parser.
5. Ingest documentation into a GraphRAG-ready corpus, including README, CDM docs, ground truth, operational log, MITRE ATT&CK pages, and relevant data components.
6. Normalize raw provenance records into typed entities, events, and semantic edges.
7. Materialize temporal graphlets around process lineage, file activity, network connections, and ground-truth attack intervals.
8. Emit schema mappings for Databricks Bronze/Silver/Gold tables.
9. Emit ArangoDB collection and edge-collection definitions.
10. Generate initial detection pattern templates and connect each pattern to supporting documentation.
11. Store all outputs with explicit lineage and confidence metadata.
```

---

# 20. Final assessment

DARPA TC E5 is one of the best public datasets for your intended demo because it has the four things you need in one ecosystem:

| Requirement                     | TC E5 fit |
| ------------------------------- | --------- |
| Temporal streaming              | Strong    |
| Heterogeneous graphlets         | Strong    |
| Natural-language support        | Strong    |
| Event recognition / explanation | Strong    |

The only material drawback is ingestion complexity: large compressed files, Avro/CDM parsing, imperfect prototype-generated data, and Drive-hosted payloads. That complexity is acceptable because it also creates a strong platform story: your system can turn messy, high-volume cyber provenance telemetry into explainable graph intelligence.

[1]: https://www.darpa.mil/research/programs/transparent-computing "TC | DARPA"
[2]: https://github.com/darpa-i2o/transparent-computing "GitHub - darpa-i2o/Transparent-Computing: Material from the DARPA Transparent Computing Program · GitHub"
[3]: https://raw.githubusercontent.com/darpa-i2o/Transparent-Computing/master/README-E3.md "raw.githubusercontent.com"
[4]: https://github.com/tanishqjasoria/darpa-tc-en5 "GitHub - tanishqjasoria/darpa-tc-en5: Instructions and tools to use data from engagement 5 of Darpa Transparent Computing Program · GitHub"
[5]: https://github.com/FiveDirections/OpTC-data "GitHub - FiveDirections/OpTC-data · GitHub"
[6]: https://attack.mitre.org/?utm_source=chatgpt.com "MITRE ATT&CK®"
[7]: https://attack.mitre.org/datacomponents/?utm_source=chatgpt.com "Data Components"
[8]: https://www.usenix.org/system/files/tapp2020-paper-khoury.pdf?utm_source=chatgpt.com "An Event-based Data Model for Granular Information Flow ..."
[9]: https://attack.mitre.org/techniques/T1543/?utm_source=chatgpt.com "Create or Modify System Process, Technique T1543"
[10]: https://www.csl.sri.com/users/gehani/papers/REP-2025.PIDDL.pdf?utm_source=chatgpt.com "On the Reproducibility of Provenance-based Intrusion ..."
