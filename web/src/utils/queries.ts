export const defaultQueryParts = {
  select:
    "SELECT id, agent_id, input_messages, input_variables, output_messages, output_error, version, duration_ds, cost_usd, created_at",
  from: "FROM completions",
  orderBy: "ORDER BY created_at DESC",
  limit: "LIMIT {limit:UInt32} OFFSET {offset:UInt32}",
};

export const buildQuery = (whereClause?: string | null) => {
  const parts = [
    defaultQueryParts.select,
    defaultQueryParts.from,
    whereClause ? `WHERE ${whereClause}` : "",
    defaultQueryParts.orderBy,
    defaultQueryParts.limit,
  ].filter(Boolean);

  return parts.join(" ");
};

export const defaultQuery = buildQuery();
