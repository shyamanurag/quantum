--  CLEAN FAKE DATA MIGRATION
-- Removes all mock virus contamination for real money futures trading

DELETE FROM trades;
DELETE FROM positions; 
DELETE FROM orders;
DELETE FROM daily_pnl;
DELETE FROM trading_sessions;

-- Reset counters
DELETE FROM sqlite_sequence WHERE name IN ('trades', 'positions', 'orders');

SELECT 'Fake data purged - Ready for real money trading' as status;
