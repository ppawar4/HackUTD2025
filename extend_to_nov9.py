#!/usr/bin/env python3
"""
Extend data from Nov 7 to end of Nov 9 (2 days)
- Proper drains in data (level drops visible)
- Same fill rates (seamless continuation)
- Noise variation (3-5%)
- Suspicious/unreported tickets
- All constraints maintained
"""

import json
import random
from datetime import datetime, timedelta, timezone
from collections import defaultdict

# Load data
print("Loading existing data...")
with open('historical_data.json', 'r') as f:
    hist = json.load(f)

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

# Build travel times
travel_times = {}
for edge in network_edges:
    key = (edge['from'], edge['to'])
    travel_times[key] = edge['travel_time_minutes']
    travel_times[(edge['to'], edge['from'])] = edge['travel_time_minutes']

def get_travel_time(from_id, to_id):
    if from_id == to_id:
        return 0
    return travel_times.get((from_id, to_id), 30)

# Fill rates (from original data analysis)
fill_rates = {
    'cauldron_001': 9.926, 'cauldron_002': 8.197, 'cauldron_003': 11.792,
    'cauldron_004': 8.437, 'cauldron_005': 7.483, 'cauldron_006': 5.031,
    'cauldron_007': 16.068, 'cauldron_008': 8.468, 'cauldron_009': 10.729,
    'cauldron_010': 9.175, 'cauldron_011': 12.310, 'cauldron_012': 7.402,
}

# Collection thresholds
collection_thresholds = {
    'cauldron_001': 0.75, 'cauldron_002': 0.70, 'cauldron_003': 0.80,
    'cauldron_004': 0.75, 'cauldron_005': 0.75, 'cauldron_006': 0.90,
    'cauldron_007': 0.75, 'cauldron_008': 0.72, 'cauldron_009': 0.70,
    'cauldron_010': 0.85, 'cauldron_011': 0.78, 'cauldron_012': 0.73,
}

# Constants
UNLOAD_TIME = 15
MAX_CAPACITY_PER_WITCH = 6000

# Witches by shift
witches_by_shift = defaultdict(list)
for courier in couriers:
    shift = courier['shift']
    witches_by_shift[shift].append(courier['courier_id'])

def get_witch_shift(timestamp):
    hour = timestamp.hour
    if 0 <= hour < 8:
        return 1
    elif 8 <= hour < 16:
        return 2
    else:
        return 3

def is_witch_available(witch_id, start_time, end_time, witch_schedules):
    if witch_id not in witch_schedules:
        return True
    for event in witch_schedules[witch_id]:
        event_start = event.get('departure_from_market') or event.get('collection_start')
        event_end = event.get('unload_complete') or event.get('collection_end')
        if event_start and event_end:
            if not (end_time <= event_start or start_time >= event_end):
                return False
    return True

# Get last entry
last_entry = hist['data'][-1]
last_timestamp = datetime.fromisoformat(last_entry['timestamp'].replace('Z', '+00:00'))
initial_levels = {k: v for k, v in last_entry['cauldron_levels'].items()}

print(f"Starting from: {last_timestamp}")
print(f"Initial levels: {initial_levels}")

# Generate Nov 8-9 (2880 minutes)
new_start = last_timestamp + timedelta(minutes=1)
new_end = datetime(2024, 11, 9, 23, 59, 0, tzinfo=timezone.utc)

print(f"\nGenerating data from {new_start} to {new_end}")
print(f"Total minutes to generate: {(new_end - new_start).total_seconds() / 60:.0f}")

# Initialize
new_historical_data = []
new_tickets = []
new_unreported_drains = []
witch_schedules = defaultdict(list)
ticket_counter = max([int(t['ticket_id'].split('_')[-1]) for t in tickets_data['transport_tickets']], default=0)

current_levels = {k: v for k, v in initial_levels.items()}
pending_drains = []  # Active drains
cauldrons_needing_collection = {}
collections_per_cauldron = defaultdict(int)

current_time = new_start
random.seed(78901)  # For reproducibility

while current_time <= new_end:
    # Start with current levels
    minute_levels = current_levels.copy()
    
    # Update levels with filling FIRST (WITH NOISE - 3-5% variation)
    for cauldron_id, current_level in minute_levels.items():
        max_vol = cauldrons[cauldron_id]['max_volume']
        fill_rate = fill_rates[cauldron_id]
        
        # Apply noise: 97% to 105% (3-5% variation)
        noise_factor = random.uniform(0.97, 1.05)
        fill_amount = fill_rate * noise_factor
        
        new_level = min(current_level + fill_amount, max_vol)
        minute_levels[cauldron_id] = round(new_level, 2)
        current_levels[cauldron_id] = new_level
    
    # THEN apply any active drains (AFTER filling, so drain accounts for simultaneous filling)
    for drain in list(pending_drains):
        # Check if current_time is within drain period (direct datetime comparison)
        if drain['start'] <= current_time <= drain['end']:
            # Apply drain - calculate net drain per minute
            # We want to achieve drain['net_drain'] total net reduction over the duration
            net_drain = drain.get('net_drain', 0)
            if drain['duration'] > 0 and net_drain > 0:
                net_drain_per_min = net_drain / drain['duration']
                current_cauldron_level = minute_levels[drain['cauldron_id']]
                new_level = max(0, current_cauldron_level - net_drain_per_min)
                minute_levels[drain['cauldron_id']] = round(new_level, 2)
                current_levels[drain['cauldron_id']] = minute_levels[drain['cauldron_id']]
        
        # Remove completed drains
        if current_time > drain['end']:
            pending_drains.remove(drain)
    
    # Check for collections needed - balanced distribution
    candidates_for_collection = []
    
    for cauldron_id, level in minute_levels.items():
        max_vol = cauldrons[cauldron_id]['max_volume']
        threshold = collection_thresholds[cauldron_id] * max_vol
        at_capacity = level >= max_vol * 0.99
        has_no_collections = collections_per_cauldron[cauldron_id] == 0
        
        if cauldron_id not in cauldrons_needing_collection:
            priority = 0
            if at_capacity:
                priority = 100  # Must collect immediately - highest priority
            elif level >= max_vol * 0.90:  # 90% full - very high priority
                priority = 95
            elif level >= threshold * 0.95:  # Near threshold - high priority
                priority = 85
            elif has_no_collections and level >= threshold * 0.80:
                priority = 75
            elif collections_per_cauldron[cauldron_id] < 2 and level >= threshold:
                priority = 65
            elif level >= threshold:
                # Collect if this cauldron has fewer than average
                avg = sum(collections_per_cauldron.values()) / max(1, len([c for c in collections_per_cauldron.values() if c > 0]))
                if collections_per_cauldron[cauldron_id] < avg * 1.3:
                    priority = 55
            # Also trigger collections for cauldrons that haven't been collected in a while
            elif collections_per_cauldron[cauldron_id] == 0 and level >= threshold * 0.70:
                priority = 45
            
            if priority > 0:
                candidates_for_collection.append((priority, cauldron_id, level))
    
    # Sort by priority (but also consider balance)
    candidates_for_collection.sort(reverse=True)
    
    # Process top candidate, but try to balance
    if candidates_for_collection:
        # If we have many candidates, prefer ones with fewer collections
        if len(candidates_for_collection) > 1:
            # Check if top 3 have very different collection counts
            top3 = candidates_for_collection[:3]
            top3_counts = [collections_per_cauldron[c[1]] for c in top3]
            min_count = min(top3_counts)
            
            # If there's a significant difference, prefer lower count
            if max(top3_counts) - min_count > 2:
                # Re-sort top 3 by collection count (fewer = higher priority)
                top3_sorted = sorted(top3, key=lambda x: (collections_per_cauldron[x[1]], -x[0]))
                candidates_for_collection = top3_sorted + candidates_for_collection[3:]
    
    if candidates_for_collection:
        priority, cauldron_id, level = candidates_for_collection[0]
        if cauldron_id not in cauldrons_needing_collection:
            max_vol = cauldrons[cauldron_id]['max_volume']
            shift = get_witch_shift(current_time)
            available_witches = witches_by_shift[shift]
            
            witch_id = None
            for w in available_witches:
                travel_to = get_travel_time('market_001', cauldron_id)
                collection_duration = random.randint(55, 85)
                travel_back = get_travel_time(cauldron_id, 'market_001')
                
                departure = current_time
                collection_start = current_time + timedelta(minutes=travel_to)
                collection_end = collection_start + timedelta(minutes=collection_duration)
                arrival_back = collection_end + timedelta(minutes=travel_back)
                unload_complete = arrival_back + timedelta(minutes=UNLOAD_TIME)
                
                if is_witch_available(w, departure, unload_complete, witch_schedules):
                    witch_id = w
                    
                    # Calculate collection
                    level_at_collection = level + (fill_rates[cauldron_id] * travel_to)
                    level_at_collection = min(level_at_collection, max_vol)  # Cap at max
                    
                    collection_percentage = random.uniform(0.60, 0.75)
                    amount_to_collect = min(level_at_collection * collection_percentage, MAX_CAPACITY_PER_WITCH)
                    
                    # Calculate net drain: amount collected is what we take, net drain in cauldron accounts for filling
                    fill_during_collection = fill_rates[cauldron_id] * collection_duration
                    # Net drain = amount collected (this is the net reduction after accounting for simultaneous filling)
                    # If we collect X liters while Y liters fill in, net drain = X
                    # But we need to ensure X > Y for a meaningful collection
                    actual_drain = amount_to_collect
                    
                    # Ensure we're actually draining something meaningful
                    if actual_drain <= fill_during_collection:
                        # Not enough - increase collection to ensure net drain
                        actual_drain = fill_during_collection + random.uniform(100, 300)
                        amount_to_collect = actual_drain
                    
                    # Cap at available level
                    actual_drain = min(actual_drain, level_at_collection)
                    actual_drain = max(50, actual_drain)  # Minimum 50L
                    
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
                    
                    # Add drain to pending - THIS WILL CAUSE LEVELS TO DROP
                    # Note: actual_drain is the net amount (already accounts for filling)
                    # We need to calculate drain rate that will achieve this net drain
                    # Net drain = drain_rate * duration - fill_rate * duration
                    # So: drain_rate = (actual_drain / duration) + fill_rate
                    total_drain_needed = actual_drain + (fill_rates[cauldron_id] * collection_duration)
                    
                    pending_drains.append({
                        'cauldron_id': cauldron_id,
                        'start': collection_start,
                        'end': collection_end,
                        'drain_amount': total_drain_needed,  # Total amount to remove (including what fills during drain)
                        'duration': collection_duration,
                        'net_drain': actual_drain  # Net amount after accounting for filling
                    })
                    
                    # Determine if suspicious (12% chance)
                    is_suspicious = random.random() < 0.12
                    reported_amount = actual_drain
                    
                    if is_suspicious:
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
                    collections_per_cauldron[cauldron_id] += 1
                    cauldrons_needing_collection[cauldron_id] = collection_end
                    
                    break
    
    # Remove completed collections from tracking
    for cauldron_id in list(cauldrons_needing_collection.keys()):
        if current_time >= cauldrons_needing_collection[cauldron_id]:
            del cauldrons_needing_collection[cauldron_id]
    
    # Store this minute's data
    new_historical_data.append({
        'timestamp': current_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'cauldron_levels': minute_levels.copy()
    })
    
    current_time += timedelta(minutes=1)

# Add unreported drains (3-4 instances)
print("\nAdding unreported drains...")
random.seed(23456)

selected_drains = []
candidate_times = [
    datetime(2024, 11, 8, 11, 30, 0, tzinfo=timezone.utc),
    datetime(2024, 11, 8, 19, 15, 0, tzinfo=timezone.utc),
    datetime(2024, 11, 9, 7, 0, 0, tzinfo=timezone.utc),
    datetime(2024, 11, 9, 16, 30, 0, tzinfo=timezone.utc),
]

for drain_start in candidate_times:
    # Find level at this time
    level_at_time = None
    for entry in new_historical_data:
        ts = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
        if abs((ts - drain_start).total_seconds()) < 60:
            level_at_time = entry['cauldron_levels']
            break
    
    if level_at_time:
        candidates = [(cid, lvl) for cid, lvl in level_at_time.items() if lvl > 200]
        if candidates:
            cauldron_id, level = random.choice(candidates)
            drain_duration = random.randint(60, 80)
            drain_end = drain_start + timedelta(minutes=drain_duration)
            
            drain_amount = min(random.uniform(200, 400), level * 0.55)
            
            selected_drains.append({
                'cauldron_id': cauldron_id,
                'drain_start': drain_start,
                'drain_end': drain_end,
                'drain_amount': drain_amount,
                'duration': drain_duration,
                'fill_rate': fill_rates[cauldron_id]
            })

# Apply unreported drains to historical data (make levels drop)
for drain in selected_drains:
    drain_rate_per_min = drain['drain_amount'] / drain['duration']
    net_drain_per_min = drain_rate_per_min - drain['fill_rate']
    
    for entry in new_historical_data:
        ts = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
        if drain['drain_start'] <= ts <= drain['drain_end']:
            if net_drain_per_min > 0:
                current_level = entry['cauldron_levels'].get(drain['cauldron_id'], 0)
                entry['cauldron_levels'][drain['cauldron_id']] = max(0, round(current_level - net_drain_per_min, 2))
    
    new_unreported_drains.append({
        'cauldron_id': drain['cauldron_id'],
        'drain_start_timestamp': drain['drain_start'].strftime('%Y-%m-%dT%H:%M:%SZ'),
        'drain_end_timestamp': drain['drain_end'].strftime('%Y-%m-%dT%H:%M:%SZ'),
        'estimated_amount_drained_liters': round(drain['drain_amount'], 2),
        'duration_minutes': drain['duration'],
        'note': 'NO TICKET EXISTS - this is an unreported drain'
    })

# Merge data
print("\nMerging data...")
hist['data'].extend(new_historical_data)
hist['metadata']['end_date'] = new_end.strftime('%Y-%m-%dT%H:%M:%SZ')
hist['metadata']['total_minutes'] = len(hist['data'])
hist['metadata']['total_collections'] = len(tickets_data['transport_tickets']) + len(new_tickets)

tickets_data['transport_tickets'].extend(new_tickets)
unreported_data['unreported_drains'].extend(new_unreported_drains)
unreported_data['metadata']['total_unreported_drains'] = len(unreported_data['unreported_drains'])

# Save
print("\nSaving files...")
with open('historical_data.json', 'w') as f:
    json.dump(hist, f, indent=2)

with open('transport_tickets.json', 'w') as f:
    json.dump(tickets_data, f, indent=2)

with open('unreported_drains.json', 'w') as f:
    json.dump(unreported_data, f, indent=2)

print(f"\n✅ Extended data to Nov 9!")
print(f"   Added {len(new_historical_data)} minutes of data")
print(f"   Added {len(new_tickets)} tickets")
print(f"   Added {len(new_unreported_drains)} unreported drains")
suspicious = sum(1 for t in new_tickets if t.get('is_suspicious'))
print(f"   Suspicious tickets: {suspicious}")
print(f"\nTicket distribution:")
for cid in sorted(collections_per_cauldron.keys()):
    print(f"   {cid}: {collections_per_cauldron[cid]}")

