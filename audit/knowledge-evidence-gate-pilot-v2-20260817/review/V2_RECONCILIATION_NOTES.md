# V2 Evidence Reconciliation Notes

Raw V2 execution evidence is present: sample manifest 24 rows, A/B pairs 24 rows, Knowledge A 24 rows, Knowledge B 24 rows, knowledge diff 16 rows, critical unresolved 8 rows, extractor critical errors 2 rows, noncritical unresolved 1 row, and 24 unique sample IDs in the audio adjudication log.

The audio adjudication JSONL contains 27 rows for 24 unique IDs. V2C004, V2C005, and V2C006 each appear twice. Rows are preserved and not silently dropped. The V2 metrics and acceptance report record the Gate decision FAIL. This publication stage does not reinterpret it.

The stage manifest also contains an earlier pre-final V2 sample contract of 22 rows, 4 controls, and 5 modules, followed by the finalized contract of 24 rows, 6 controls, and 6 modules. The finalized block is the authoritative current contract; the earlier block is retained as superseded history and is not silently overwritten.

The source package metadata is named V2_SOURCE_PACKAGE_INFO.json in this review copy. Its statement that binary audio clips were included applies to the original V2 ZIP, not to this text-only ChatGPT review package.
