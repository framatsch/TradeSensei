-- Split-aware integrity checks

-- 1) Split children must have parent lineage
SELECT COUNT(*) AS split_children_without_parent
FROM logical_executions
WHERE origin = 'split' AND parent_id IS NULL;

-- 2) Quantity conservation per split parent
SELECT
  p.id AS parent_id,
  p.quantity AS parent_qty,
  SUM(c.quantity) AS children_qty
FROM logical_executions p
JOIN logical_executions c ON c.parent_id = p.id
WHERE c.origin = 'split'
GROUP BY p.id, p.quantity
HAVING p.quantity <> SUM(c.quantity);

-- 3) Commission conservation per split parent
SELECT
  p.id AS parent_id,
  p.commission AS parent_commission,
  SUM(c.commission) AS children_commission
FROM logical_executions p
JOIN logical_executions c ON c.parent_id = p.id
WHERE c.origin = 'split'
GROUP BY p.id, p.commission
HAVING p.commission <> SUM(c.commission);

-- 4) Active orphan split children (should be 0 after import finalization)
SELECT COUNT(*) AS orphan_split_children
FROM logical_executions
WHERE origin = 'split' AND deleted = false AND trade_id IS NULL;
