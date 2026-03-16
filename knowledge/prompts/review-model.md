# Review dbt Model: {{model_name}}

You are reviewing the dbt model `{{model_name}}` for semantic issues.

## Model SQL

```sql
{{model_sql}}
```

## Review Focus

Check for the following semantic issues (in order of importance):

1. **Join fanout risk** — Does any join multiply rows unexpectedly?
   - Is the grain of the model preserved after each join?
   - Are many-to-one relationships aggregated before joining?

2. **Data completeness** — Are there suspicious WHERE clauses?
   - Does filtering on status/type values risk silently dropping valid rows?
   - Are NULL values handled appropriately?

3. **Model responsibility** — Is this model doing too much?
   - Should complex logic be split into an intermediate model?
   - Are there CTEs that should be their own models?

4. **Code quality** — Is the SQL clear and maintainable?
   - Are aliases meaningful?
   - Is the intent clear from the SQL structure?

Use `get_rules` to review the knowledge base, then `add_finding` for each issue discovered.
