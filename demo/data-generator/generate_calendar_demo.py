#!/usr/bin/env python3
import random
import hashlib
from datetime import datetime, timedelta
from uuid import UUID
import clickhouse_connect
from clickhouse_connect.driver.client import Client

def generate_uuid7() -> UUID:
    """Generate a UUIDv7 with proper timestamp encoding"""
    import time
    import secrets
    
    # Get current timestamp in milliseconds
    timestamp_ms = int(time.time() * 1000)
    
    # UUIDv7 format:
    # 48 bits timestamp (ms since Unix epoch)
    # 4 bits version (0111 = 7)
    # 12 bits random
    # 2 bits variant (10)
    # 62 bits random
    
    timestamp_bytes = timestamp_ms.to_bytes(6, 'big')
    random_bytes = secrets.token_bytes(10)
    
    # Combine timestamp and random parts
    uuid_bytes = bytearray(timestamp_bytes + random_bytes)
    
    # Set version (7) and variant bits
    uuid_bytes[6] = (uuid_bytes[6] & 0x0F) | 0x70  # Version 7
    uuid_bytes[8] = (uuid_bytes[8] & 0x3F) | 0x80  # Variant 10
    
    return UUID(bytes=bytes(uuid_bytes))

def generate_uuid7_for_date(target_date: datetime) -> UUID:
    """Generate a UUIDv7 for a specific date/time"""
    import secrets
    
    # Convert target date to milliseconds since Unix epoch
    timestamp_ms = int(target_date.timestamp() * 1000)
    
    timestamp_bytes = timestamp_ms.to_bytes(6, 'big')
    random_bytes = secrets.token_bytes(10)
    
    uuid_bytes = bytearray(timestamp_bytes + random_bytes)
    uuid_bytes[6] = (uuid_bytes[6] & 0x0F) | 0x70  # Version 7
    uuid_bytes[8] = (uuid_bytes[8] & 0x3F) | 0x80  # Variant 10
    
    return UUID(bytes=bytes(uuid_bytes))

def generate_fixed_string(content: str, length: int = 32) -> str:
    """Generate a fixed-length string hash"""
    return hashlib.md5(content.encode()).hexdigest()[:length]

def get_daily_completion_count(day_of_week: int, is_holiday: bool = False) -> int:
    """Get realistic number of completions for a given day"""
    if is_holiday:
        return random.randint(5, 15)
    elif day_of_week < 5:  # Weekday
        # Business hours have more activity
        base = random.randint(60, 90)
        # Add some variance
        return base + random.randint(-10, 20)
    else:  # Weekend
        return random.randint(15, 30)

def get_realistic_cost() -> float:
    """Generate realistic cost distribution"""
    rand = random.random()
    if rand < 0.70:  # 70% simple extractions
        return random.uniform(0.002, 0.005)
    elif rand < 0.95:  # 25% medium complexity
        return random.uniform(0.01, 0.02)
    else:  # 5% complex
        return random.uniform(0.03, 0.08)

def get_realistic_latency() -> float:
    """Generate realistic latency distribution for P99 analysis
    Returns duration in seconds with realistic distribution"""
    rand = random.random()
    if rand < 0.50:  # 50% fast responses
        return random.uniform(0.3, 0.8)  # 300-800ms
    elif rand < 0.90:  # 40% normal responses
        return random.uniform(0.8, 1.5)  # 800ms-1.5s
    elif rand < 0.99:  # 9% slower responses
        return random.uniform(1.5, 3.0)  # 1.5-3s
    else:  # 1% outliers (affects P99)
        return random.uniform(3.0, 5.0)  # 3-5s

def generate_completion_data(date: datetime, agent_id: str, tenant_uid: int = 1):
    """Generate a single completion record"""
    # Generate UUID7 for this specific timestamp
    completion_id = generate_uuid7_for_date(date)
    
    # Calculate cost
    cost = get_realistic_cost()
    cost_millionth_usd = int(cost * 1_000_000)
    
    # Generate realistic latency
    duration_seconds = get_realistic_latency()
    duration_ds = int(duration_seconds * 10)  # Convert to deciseconds
    
    # Generate fixed-string IDs
    version_id = generate_fixed_string(f"version_{agent_id}")
    input_id = generate_fixed_string(f"input_{completion_id}")
    output_id = generate_fixed_string(f"output_{completion_id}")
    
    # Success rate ~95%
    output_error = "" if random.random() < 0.95 else '{"error": "Request timeout"}'
    
    return {
        'tenant_uid': tenant_uid,
        'id': completion_id,
        'agent_id': agent_id,
        'updated_at': date,
        'version_id': version_id,
        'version_model': random.choice(['gpt-3.5-turbo', 'gpt-4', 'claude-3-haiku']),
        'version': '{"prompt": "Extract calendar events"}',
        'input_id': input_id,
        'input_preview': 'Extract events from: Meeting tomorrow at 3pm...',
        'input_messages': '[]',
        'input_variables': '{"text": "Meeting tomorrow at 3pm"}',
        'output_id': output_id,
        'output_preview': 'Found 1 event: Meeting at 3pm',
        'output_messages': '[]',
        'output_error': output_error,
        'messages': '[]',
        'duration_ds': duration_ds,
        'cost_millionth_usd': cost_millionth_usd,
        'metadata': {'environment': random.choice(['prod', 'staging'])},
        'source': 2,  # api
        'traces.kind': [],
        'traces.model': [],
        'traces.provider': [],
        'traces.usage': [],
        'traces.name': [],
        'traces.tool_input_preview': [],
        'traces.tool_output_preview': [],
        'traces.duration_ds': [],
        'traces.cost_millionth_usd': []
    }

def main():
    print("🚀 Connecting to ClickHouse...")
    
    # Connect to ClickHouse
    client = clickhouse_connect.get_client(
        host='localhost',
        port=8123,
        username='default',
        password='admin',
        database='db'
    )
    
    print("✅ Connected to ClickHouse")
    
    agent_id = "calendar-event-extractor"
    tenant_uid = 2  # Using tenant_uid 2 based on current system data
    
    # Generate data for last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    current_date = start_date
    total_completions = 0
    
    print(f"\n📅 Generating data from {start_date.date()} to {end_date.date()}")
    print(f"🤖 Agent ID: {agent_id}\n")
    
    while current_date <= end_date:
        # Determine number of completions for this day
        day_count = get_daily_completion_count(current_date.weekday())
        
        day_completions = []
        for i in range(day_count):
            # Spread completions throughout the day with business hours bias
            hour = random.choices(
                range(24),
                weights=[1, 1, 1, 1, 1, 2, 3, 5, 10, 12, 12, 11, 11, 10, 8, 6, 4, 3, 2, 1, 1, 1, 1, 1],
                k=1
            )[0]
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            
            completion_time = current_date.replace(hour=hour, minute=minute, second=second)
            
            completion = generate_completion_data(completion_time, agent_id, tenant_uid)
            day_completions.append(completion)
        
        # Batch insert for this day
        if day_completions:
            # Convert data to proper format for clickhouse-connect
            data_to_insert = []
            columns = list(day_completions[0].keys())
            
            for completion in day_completions:
                row = [completion[col] for col in columns]
                data_to_insert.append(row)
            
            client.insert(
                'completions',
                data_to_insert,
                column_names=columns
            )
            
            total_completions += len(day_completions)
            print(f"✓ {current_date.date()}: {len(day_completions)} completions")
        
        current_date += timedelta(days=1)
    
    print(f"\n✅ Successfully generated {total_completions} completions!")
    
    # Verify the data with latency percentiles
    result = client.query(f"""
        SELECT 
            toDate(created_at) as date,
            COUNT(*) as count,
            ROUND(AVG(cost_usd), 4) as avg_cost,
            ROUND(SUM(cost_usd), 2) as total_cost,
            ROUND(quantile(0.50)(duration_seconds), 2) as p50_latency,
            ROUND(quantile(0.95)(duration_seconds), 2) as p95_latency,
            ROUND(quantile(0.99)(duration_seconds), 2) as p99_latency
        FROM completions 
        WHERE agent_id = '{agent_id}'
          AND created_at >= now() - INTERVAL 30 DAY
        GROUP BY date
        ORDER BY date DESC
        LIMIT 5
    """)
    
    print("\n📊 Sample of generated data (last 5 days):")
    print("Date       | Count | Avg Cost | Total Cost | P50 Lat | P95 Lat | P99 Lat")
    print("-----------|-------|----------|------------|---------|---------|--------")
    for row in result.result_rows:
        print(f"{row[0]} | {row[1]:5d} | ${row[2]:.4f} | ${row[3]:6.2f} | {row[4]:5.2f}s | {row[5]:5.2f}s | {row[6]:5.2f}s")

if __name__ == "__main__":
    main()