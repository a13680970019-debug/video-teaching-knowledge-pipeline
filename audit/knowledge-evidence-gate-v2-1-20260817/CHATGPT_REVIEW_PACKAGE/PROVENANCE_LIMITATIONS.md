# Provenance limitations

The V2 command ledger and output artifacts do not bind an execution-time source hash. The current replay therefore records `EXECUTED_SOURCE_VERSION_HASH_BOUND = false`, `SOURCE_VERSION_AT_EXECUTION = UNPROVEN`, and labels the current implementation `AUTHORITATIVE_CURRENT_SNAPSHOT`.

The baseline replay is semantically reproduced and metrics are equal, but it is not byte-identical because of runtime timestamps, sandbox paths, and three duplicated published audio rows.
