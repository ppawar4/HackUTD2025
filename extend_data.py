#!/usr/bin/env python3
"""
Extend historical data and tickets by 2 more days
Maintains all constraints: fill rates, witch shifts, travel times, suspicious tickets, unreported drains
"""

import json
import random
from datetime import datetime, timedelta
from collections import defaultdict

# Load existing data
print("Loading existing data...")
with open('historical_data.json', 'r') as f:
    historical_data = json.load(f)

with open('cauldrons.json', 'r') as f:
    cauldrons_data = json.load(f)

with open('transport_tickets.json', 'r') as f:
    tickets_data = json.load(f)

with open('unreported_drains.json', 'r') as f:
    unreported_data = json.load(f)

# Extract data
cauldrons = {c['id']: c for c in cauldrons_data['cauldrons']}
network_edges = cauldrons_data['network']['edges']
couriers = cauldrons_data['couriers']
existing_tickets = tickets_data['transport_tickets']
existing_unreported = unreported_data['unreported_drains']

# Get last entry from historical data
last_entry = historical_data['data'][-1]
last_timestamp = datetime.fromisoformat(last_entry['timestamp'].replace('Z', '+00:00'))
initial_levels = {k: v for k, v in last_entry['cauldron_levels'].items()}

print(f"Last timestamp: {last_timestamp}")
print(f"Starting levels: {initial_levels}")

# Build travel time lookup
travel_times = {}
for edge in network_edges:
    key = (edge['from'], edge['to'])
    travel_times[key] = edge['travel_time_minutes']
    travel_times[(edge['to'], edge['from'])] = edge['travel_time_minutes']

def get_travel_time(from_id, to_id):
    """Get travel time between two locations"""
    if from_id == to_id:
        return 0
    return travel_times.get((from_id, to_id), 30)  # Default 30 min

# Define fill rates per cauldron (liters per minute) - from analyzing original data
fill_rates = {
    'cauldron_001': 9.926,   # High producer
    'cauldron_002': 8.197,   # Medium
    'cauldron_003': 11.792,  # Very high producer
    'cauldron_004': 8.437,   # Medium-high
    'cauldron_005': 7.483,   # Medium
    'cauldron_006': 5.031,   # Slow (doesn't need daily pickups)
    'cauldron_007': 16.068,  # Very high producer
    'cauldron_008': 8.468,   # Medium-high
    'cauldron_009': 10.729,  # High
    'cauldron_010': 9.175,   # Medium-high (slower than others)
    'cauldron_011': 12.310,  # Very high producer
    'cauldron_012': 7.402,   # Medium
}

# Collection thresholds (start collecting when level reaches this %)
# Adjusted based on new fill rates
collection_thresholds = {
    'cauldron_001': 0.75,
    'cauldron_002': 0.70,
    'cauldron_003': 0.80,
    'cauldron_004': 0.75,
    'cauldron_005': 0.75,
    'cauldron_006': 0.90,  # Slow, wait longer
    'cauldron_007': 0.75,  # High producer but adjusted
    'cauldron_008': 0.72,
    'cauldron_009': 0.70,
    'cauldron_010': 0.85,  # Medium-slow, wait longer
    'cauldron_011': 0.78,
    'cauldron_012': 0.73,
}

# Constants
UNLOAD_TIME = 15  # minutes
MAX_CAPACITY_PER_WITCH = 6000  # liters
NOISE_VARIATION = 0.03  # 3% noise (3-5% variation range)

# Witches by shift
witches_by_shift = defaultdict(list)
for courier in couriers:
    shift = courier['shift']
    witches_by_shift[shift].append(courier['courier_id'])

def get_witch_shift(timestamp):
    """Get which shift a timestamp falls into"""
    hour = timestamp.hour
    if 0 <= hour < 8:
        return 1
    elif 8 <= hour < 16:
        return 2
    else:
        return 3

def is_witch_available(witch_id, start_time, end_time, witch_schedules):
    """Check if a witch is available during a time period"""
    if witch_id not in witch_schedules:
        return True
    for event in witch_schedules[witch_id]:
        event_start = event.get('departure_from_market') or event.get('collection_start')
        event_end = event.get('unload_complete') or event.get('collection_end')
        if event_start and event_end:
            # Check for overlap
            if not (end_time <= event_start or start_time >= event_end):
                return False
    return True

# Generate 2 days of data (2880 minutes)
new_start = last_timestamp + timedelta(minutes=1)
new_end = new_start + timedelta(days=2) - timedelta(minutes=1)

print(f"\nGenerating data from {new_start} to {new_end}")
print(f"Total minutes to generate: {(new_end - new_start).total_seconds() / 60:.0f}")

# Initialize
new_historical_data_entries = []
new_tickets = []
new_unreported_drains = []
witch_schedules = defaultdict(list)
ticket_counter = max([int(t['ticket_id'].split('_')[-1]) for t in existing_tickets], default=0)

# Track levels as we generate
current_levels = {k: v for k, v in initial_levels.items()}

# Track pending collections (scheduled but not yet applied)
pending_collections = []

# Track which cauldrons need collection
cauldrons_needing_collection = {}

# Generate data minute by minute
current_time = new_start
minute_index = 0

while current_time <= new_end:
    # Update levels based on fill rates
    minute_levels = {}
    for cauldron_id, current_level in current_levels.items():
        max_vol = cauldrons[cauldron_id]['max_volume']
        fill_rate = fill_rates[cauldron_id]
        
        # Add filling (with noise - 3-5% variation like original data)
        # Use range: 0.97 to 1.03 for ~3% variation, matching original data pattern
        noise = random.uniform(0.97, 1.03)
        new_level = min(current_level + (fill_rate * noise), max_vol)
        minute_levels[cauldron_id] = round(new_level, 2)
        current_levels[cauldron_id] = new_level
    
    # Check for collections needed
    for cauldron_id, level in minute_levels.items():
        max_vol = cauldrons[cauldron_id]['max_volume']
        threshold = collection_thresholds[cauldron_id] * max_vol
        at_capacity = level >= max_vol * 0.99
        
        # Check if we need a collection (and haven't already scheduled one)
        if (level >= threshold or at_capacity) and cauldron_id not in cauldrons_needing_collection:
            # Schedule a collection
            shift = get_witch_shift(current_time)
            available_witches = [w for w in witches_by_shift[shift]]
            
            if available_witches:
                # Try to find an available witch
                witch_id = None
                for w in available_witches:
                    # Estimate timing
                    travel_to = get_travel_time('market_001', cauldron_id)
                    collection_duration = random.randint(50, 90)
                    travel_back = get_travel_time(cauldron_id, 'market_001')
                    
                    departure = current_time
                    collection_start = current_time + timedelta(minutes=travel_to)
                    collection_end = collection_start + timedelta(minutes=collection_duration)
                    arrival_back = collection_end + timedelta(minutes=travel_back)
                    unload_complete = arrival_back + timedelta(minutes=UNLOAD_TIME)
                    
                    if is_witch_available(w, departure, unload_complete, witch_schedules):
                        witch_id = w
                        break
                
                if witch_id:
                    # Schedule the collection
                    travel_to = get_travel_time('market_001', cauldron_id)
                    collection_duration = random.randint(50, 90)
                    travel_back = get_travel_time(cauldron_id, 'market_001')
                    
                    departure = current_time
                    collection_start = current_time + timedelta(minutes=travel_to)
                    collection_end = collection_start + timedelta(minutes=collection_duration)
                    arrival_back = collection_end + timedelta(minutes=travel_back)
                    unload_complete = arrival_back + timedelta(minutes=UNLOAD_TIME)
                    
                    # Calculate collection amount
                    level_at_collection = level + (fill_rates[cauldron_id] * travel_to)
                    collection_percentage = random.uniform(0.60, 0.80)
                    amount_to_collect = min(level_at_collection * collection_percentage, MAX_CAPACITY_PER_WITCH)
                    
                    # Account for filling during collection
                    fill_during_collection = fill_rates[cauldron_id] * collection_duration
                    actual_drain = amount_to_collect - fill_during_collection
                    actual_drain = max(0, min(actual_drain, level_at_collection))
                    
                    # Schedule event
                    schedule_event = {
                        'departure_from_market': departure,
                        'collection_start': collection_start,
                        'collection_end': collection_end,
                        'unload_complete': unload_complete,
                        'cauldron_id': cauldron_id,
                        'actual_drain': actual_drain,
                        'witch_id': witch_id
                    }
                    witch_schedules[witch_id].append(schedule_event)
                    pending_collections.append({
                        'cauldron_id': cauldron_id,
                        'start': collection_start,
                        'end': collection_end,
                        'amount': actual_drain,
                        'witch_id': witch_id
                    })
                    
                    # Determine if suspicious (12% chance)
                    is_suspicious = random.random() < 0.12
                    reported_amount = actual_drain
                    
                    if is_suspicious:
                        # Underreported: ticket reports less than actual
                        underreport_factor = random.uniform(0.75, 0.92)
                        reported_amount = actual_drain * underreport_factor
                    
                    # Create ticket
                    ticket_counter += 1
                    date_str = collection_start.strftime('%Y%m%d')
                    ticket_id = f"TT_{date_str}_{ticket_counter:03d}"
                    
                    ticket = {
                        'ticket_id': ticket_id,
                        'cauldron_id': cauldron_id,
                        'collection_start_timestamp': collection_start.strftime('%Y-%m-%dT%H:%M:%SZ'),
                        'collection_timestamp': collection_end.strftime('%Y-%m-%dT%H:%M:%SZ'),
                        'amount_collected': round(reported_amount, 2),
                        'courier_id': witch_id,
                        'status': 'completed',
                        'notes': 'Sequential collection'
                    }
                    
                    if is_suspicious:
                        ticket['is_suspicious'] = True
                        ticket['suspicious_type'] = 'underreported'
                        ticket['_actual_amount_collected'] = round(actual_drain, 2)
                    
                    new_tickets.append(ticket)
                    cauldrons_needing_collection[cauldron_id] = collection_end
    
    # Check if any collections have completed and should reset the flag
    for cauldron_id in list(cauldrons_needing_collection.keys()):
        if current_time >= cauldrons_needing_collection[cauldron_id]:
            del cauldrons_needing_collection[cauldron_id]
    
    # Apply any active drains to levels (before storing)
    for drain in list(pending_collections):
        if drain['start'] <= current_time <= drain['end']:
            # Drain is active
            drain_duration = (drain['end'] - drain['start']).total_seconds() / 60
            if drain_duration > 0:
                # Calculate drain rate (total amount / duration)
                total_drain = drain['amount']
                drain_rate_per_minute = total_drain / drain_duration
                # Net drain = drain rate - fill rate (accounting for continuous filling)
                net_drain_rate = drain_rate_per_minute - fill_rates[drain['cauldron_id']]
                if net_drain_rate > 0:
                    minute_levels[drain['cauldron_id']] = max(0, minute_levels[drain['cauldron_id']] - net_drain_rate)
                    current_levels[drain['cauldron_id']] = minute_levels[drain['cauldron_id']]
        
        # Remove completed drains
        if current_time > drain['end']:
            pending_collections.remove(drain)
    
    # Store this minute's data
    new_historical_data_entries.append({
        'timestamp': current_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'cauldron_levels': minute_levels.copy()
    })
    
    current_time += timedelta(minutes=1)
    minute_index += 1

# Add unreported drains (3-4 instances)
print("\nAdding unreported drains...")
unreported_count = random.randint(3, 4)

# Build a set of busy times from scheduled collections
busy_times = set()
for witch_id, events in witch_schedules.items():
    for event in events:
        start = event.get('collection_start') or event.get('departure_from_market')
        end = event.get('unload_complete') or event.get('collection_end')
        if start and end:
            # Mark all minutes in this range as busy
            t = start
            while t <= end:
                busy_times.add(t)
                t += timedelta(minutes=1)

# Find times for unreported drains (when no collections are happening)
selected_unreported = []
for attempt in range(20):  # Try up to 20 times to find good spots
    hour_offset = random.randint(6, 42)  # Avoid very early/late hours
    check_time = new_start + timedelta(hours=hour_offset)
    
    # Skip if this time is busy
    if check_time in busy_times:
        continue
    
    # Find level at this time
    level_at_time = None
    for entry in new_historical_data_entries:
        ts = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
        if abs((ts - check_time).total_seconds()) < 60:
            level_at_time = entry['cauldron_levels']
            break
    
    if level_at_time:
        # Pick a random cauldron with sufficient level
        candidates = [(cid, lvl) for cid, lvl in level_at_time.items() if lvl > 150]
        if candidates:
            cauldron_id, level = random.choice(candidates)
            # Check if we already have a drain for this cauldron nearby
            too_close = any(
                d['cauldron_id'] == cauldron_id and
                abs((datetime.fromisoformat(d['drain_start_timestamp'].replace('Z', '+00:00')) - check_time).total_seconds()) < 14400
                for d in selected_unreported
            )
            if not too_close:
                selected_unreported.append({
                    'time': check_time,
                    'cauldron_id': cauldron_id,
                    'level': level
                })
                if len(selected_unreported) >= unreported_count:
                    break

# Process selected unreported drains
for drain_info in selected_unreported:
    cauldron_id = drain_info['cauldron_id']
    drain_start = drain_info['time']
    drain_duration = random.randint(50, 80)
    drain_end = drain_start + timedelta(minutes=drain_duration)
    
    # Find level at start
    level_at_start = None
    for entry in new_historical_data_entries:
        ts = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
        if abs((ts - drain_start).total_seconds()) < 60:
            level_at_start = entry['cauldron_levels'].get(cauldron_id, 0)
            break
    
    if level_at_start and level_at_start > 50:
        fill_during_drain = fill_rates[cauldron_id] * drain_duration
        drain_amount = min(random.uniform(150, 350), level_at_start * 0.6)
        actual_drain = drain_amount
        
        # Apply drain to historical data
        for entry in new_historical_data_entries:
            ts = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
            if drain_start <= ts <= drain_end:
                drain_duration_min = (drain_end - drain_start).total_seconds() / 60
                if drain_duration_min > 0:
                    drain_rate = (actual_drain / drain_duration_min)
                    net_drain_rate = drain_rate - fill_rates[cauldron_id]
                    if net_drain_rate > 0:
                        entry['cauldron_levels'][cauldron_id] = max(0, 
                            entry['cauldron_levels'][cauldron_id] - net_drain_rate)
        
        new_unreported_drains.append({
            'cauldron_id': cauldron_id,
            'drain_start_timestamp': drain_start.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'drain_end_timestamp': drain_end.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'estimated_amount_drained_liters': round(actual_drain, 2),
            'duration_minutes': drain_duration,
            'note': 'NO TICKET EXISTS - this is an unreported drain'
        })

# Merge with existing data
print("\nMerging data...")
historical_data['data'].extend(new_historical_data_entries)
historical_data['metadata']['end_date'] = new_end.strftime('%Y-%m-%dT%H:%M:%SZ')
historical_data['metadata']['total_minutes'] = len(historical_data['data'])
historical_data['metadata']['total_collections'] = len(existing_tickets) + len(new_tickets)

# Merge tickets
tickets_data['transport_tickets'].extend(new_tickets)

# Merge unreported drains
unreported_data['unreported_drains'].extend(new_unreported_drains)
unreported_data['metadata']['total_unreported_drains'] = len(unreported_data['unreported_drains'])

# Save updated files
print("\nSaving updated files...")
with open('historical_data.json', 'w') as f:
    json.dump(historical_data, f, indent=2)

with open('transport_tickets.json', 'w') as f:
    json.dump(tickets_data, f, indent=2)

with open('unreported_drains.json', 'w') as f:
    json.dump(unreported_data, f, indent=2)

print(f"\n✅ Extension complete!")
print(f"   Added {len(new_historical_data_entries)} minutes of historical data")
print(f"   Added {len(new_tickets)} new transport tickets")
print(f"   Added {len(new_unreported_drains)} new unreported drains")
suspicious_count = sum(1 for t in new_tickets if t.get('is_suspicious'))
print(f"   Suspicious tickets in new data: {suspicious_count}")
print(f"   Data now extends to: {new_end}")
