# Assess Join Pattern: {{model_name}}

Analyze the join patterns in this dbt model for fanout risk.

## Model SQL

```sql
{{model_sql}}
```

## Join Analysis Checklist

For each join in the model:

1. **Identify the grain** — What does one row represent in each table being joined?
2. **Check cardinality** — Is this a 1:1, 1:many, or many:many join?
3. **Verify aggregation** — If joining a 1:many, is the many side aggregated first?
4. **Test for fanout** — After the join, is the grain of the primary table preserved?

## Expected Output

Use `add_finding` with rule_id `join_fanout` if you identify any fanout risk.
Include in the message:
- Which tables are being joined
- The suspected cardinality
- Why it causes fanout
- How to fix it (aggregate the many side first)
