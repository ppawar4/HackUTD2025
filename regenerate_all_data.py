#!/usr/bin/env python3
"""
Regenerate ALL data from Oct 30, 2024 to Nov 9, 2024 (end of day)
with all constraints:
- Proper fill rates (same as original)
- Noise variation (3-5%)
- Drains that actually work (levels drop)
- Suspicious and unreported tickets
- Witch shifts and travel times
- Balanced collections (no cauldrons stuck at max)
"""

import json
import random
from datetime import datetime, timedelta, timezone
from collections import defaultdict

# Load cauldrons data
print("Loading cauldrons data...")
with open('cauldrons.json', 'r') as f:
    cauldrons_data = json.load(f)

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

# Fill rates - REDUCED EVEN FURTHER (about 50% of previous rates)
# Creates variation: some very slow, some moderately slow
fill_rates = {
    'cauldron_001': 0.090,  # Reduced from 0.149 (was hitting capacity too often)
    'cauldron_002': 0.020,  # Keep same (low rate)
    'cauldron_003': 0.059,  # Keep same (moderate rate)
    'cauldron_004': 0.075,  # Reduced from 0.127 (was hitting capacity too often)
    'cauldron_005': 0.019,  # Keep same (low rate)
    'cauldron_006': 0.013,  # Keep same (lowest rate)
    'cauldron_007': 0.065,  # Further reduced to prevent hitting capacity for too long
    'cauldron_008': 0.043,  # Keep same (moderate rate)
    'cauldron_009': 0.095,  # Reduced from 0.161 (was hitting capacity too often)
    'cauldron_010': 0.023,  # Keep same (low rate)
    'cauldron_011': 0.110,  # Reduced from 0.185 (was hitting capacity too often)
    'cauldron_012': 0.037,  # Keep same (moderate rate)
}

# Collection thresholds (percentage of max volume) - LOWERED to generate more tickets (more frequent collections needed)
collection_thresholds = {
    'cauldron_001': 0.30, 'cauldron_002': 0.25, 'cauldron_003': 0.35,
    'cauldron_004': 0.30, 'cauldron_005': 0.30, 'cauldron_006': 0.40,
    'cauldron_007': 0.30, 'cauldron_008': 0.28, 'cauldron_009': 0.25,
    'cauldron_010': 0.35, 'cauldron_011': 0.32, 'cauldron_012': 0.28,
}

# Constants
UNLOAD_TIME = 15
MAX_CAPACITY_PER_WITCH = 500  # Further reduced from 1000L to 500L
MIN_BUFFER_BETWEEN_TRIPS = 10  # Minimum minutes between trips for safety/preparation

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
    """Check if witch is available for the entire period, including buffer time"""
    if witch_id not in witch_schedules:
        return True
    # Add buffer before start and after end to ensure adequate spacing
    buffer_start = start_time - timedelta(minutes=MIN_BUFFER_BETWEEN_TRIPS)
    buffer_end = end_time + timedelta(minutes=MIN_BUFFER_BETWEEN_TRIPS)
    
    for event in witch_schedules[witch_id]:
        event_start = event.get('departure_from_market') or event.get('collection_start')
        event_end = event.get('unload_complete') or event.get('collection_end')
        if event_start and event_end:
            # Check if there's any overlap (including buffers)
            if not (buffer_end <= event_start or buffer_start >= event_end):
                return False
    return True

# Initialize
start_date = datetime(2024, 10, 30, 0, 0, 0, tzinfo=timezone.utc)
end_date = datetime(2024, 11, 9, 23, 59, 0, tzinfo=timezone.utc)

total_minutes = int((end_date - start_date).total_seconds() / 60) + 1
print(f"\nGenerating data from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
print(f"Total minutes: {total_minutes:,}")

# Initialize levels (start at reasonable levels)
initial_levels = {}
for cauldron_id, cauldron in cauldrons.items():
    max_vol = cauldron['max_volume']
    # Start at 20-40% of capacity
    initial_levels[cauldron_id] = random.uniform(max_vol * 0.20, max_vol * 0.40)

print(f"Initial levels: {initial_levels}")

# Data structures
historical_data = []
transport_tickets = []
unreported_drains = []
witch_schedules = defaultdict(list)
pending_drains = []  # Active drains
cauldrons_needing_collection = {}
collections_per_cauldron = defaultdict(int)
ticket_counter = 0

current_levels = {k: v for k, v in initial_levels.items()}
current_time = start_date
random.seed(12345)  # For reproducibility

print("\nGenerating data...")
progress_interval = total_minutes // 10

while current_time <= end_date:
    # Start with current levels
    minute_levels = current_levels.copy()
    
    # Update levels with filling FIRST (WITH SLIGHTLY MORE NOISE)
    for cauldron_id, current_level in minute_levels.items():
        max_vol = cauldrons[cauldron_id]['max_volume']
        fill_rate = fill_rates[cauldron_id]
        
        # Apply noise: 96% to 104% (4% variation) - slightly more than before
        base_noise_factor = random.uniform(0.96, 1.04)
        
        # Occasional larger variations (4% chance)
        if random.random() < 0.04:
            spike_factor = random.uniform(0.94, 1.06)  # Larger variation occasionally
        else:
            spike_factor = 1.0
        
        noise_factor = base_noise_factor * spike_factor
        fill_amount = fill_rate * noise_factor
        
        # Jitter (±0.15% of current level) - slightly more than before
        jitter = random.uniform(-0.0015, 0.0015) * current_level
        
        new_level = min(current_level + fill_amount + jitter, max_vol)
        # Ensure level doesn't go negative
        new_level = max(0, new_level)
        
        minute_levels[cauldron_id] = round(new_level, 2)
        current_levels[cauldron_id] = new_level
    
    # THEN apply any active drains (AFTER filling, so drain accounts for simultaneous filling)
    for drain in list(pending_drains):
        # Check if current_time is within drain period
        if drain['start'] <= current_time <= drain['end']:
            # Apply drain - calculate net drain per minute
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
    # CRITICAL: First check if ANY cauldron is at capacity - these need immediate attention
    at_capacity_cauldrons = []
    regular_candidates = []
    
    for cauldron_id, level in minute_levels.items():
        max_vol = cauldrons[cauldron_id]['max_volume']
        threshold = collection_thresholds[cauldron_id] * max_vol
        at_capacity = level >= max_vol * 0.99
        has_no_collections = collections_per_cauldron[cauldron_id] == 0
        
        if cauldron_id not in cauldrons_needing_collection:
            priority = 0
            # CRITICAL: At capacity - highest priority always
            if at_capacity:
                priority = 100
            # Very high priority for cauldrons near capacity
            elif level >= max_vol * 0.90:  # 90% full
                priority = 98
            elif level >= max_vol * 0.80:  # 80% full
                priority = 95
            elif level >= max_vol * 0.70:  # 70% full
                priority = 90
            # High priority for cauldrons at threshold
            elif level >= threshold:
                priority = 85
            # Medium-high priority for cauldrons near threshold
            elif level >= threshold * 0.85:
                priority = 80
            # Medium priority for cauldrons at 70% of threshold
            elif level >= threshold * 0.70:
                priority = 75
            # Medium-low priority for cauldrons at 55% of threshold
            elif level >= threshold * 0.55:
                priority = 70
            # Priority for uncollected cauldrons at lower levels
            elif has_no_collections and level >= max_vol * 0.40:
                priority = 70
            elif has_no_collections and level >= max_vol * 0.30:
                priority = 65
            # Lower priority but still collect if below threshold but no collections yet
            elif collections_per_cauldron[cauldron_id] == 0 and level >= max_vol * 0.25:
                priority = 60
            # Even lower priority for more frequent collections - collect at 25-30% if no recent collection
            elif level >= max_vol * 0.30 and collections_per_cauldron[cauldron_id] < 5:
                priority = 55
            elif level >= max_vol * 0.25 and collections_per_cauldron[cauldron_id] < 3:
                priority = 50
            elif level >= max_vol * 0.20:
                priority = 45
            
            if priority > 0:
                if at_capacity:
                    at_capacity_cauldrons.append((priority, cauldron_id, level))
                else:
                    regular_candidates.append((priority, cauldron_id, level))
    
    # Prioritize at-capacity cauldrons first, then regular candidates
    candidates_for_collection = at_capacity_cauldrons + regular_candidates
    
    # Sort by priority (but also consider balance)
    # Balance is important - prefer cauldrons with fewer collections if priority is similar
    candidates_for_collection.sort(reverse=True)
    
    # Process top candidate, but try to balance
    if candidates_for_collection:
        # Strong balancing: if top candidate has many more collections than others, prefer others
        if len(candidates_for_collection) > 1:
            top_priority = candidates_for_collection[0][0]
            top_cid = candidates_for_collection[0][1]
            top_collections = collections_per_cauldron[top_cid]
            
            # Find candidates with same or similar priority but fewer collections
            for i, (pri, cid, lev) in enumerate(candidates_for_collection[1:], 1):
                if pri >= top_priority - 5 and collections_per_cauldron[cid] < top_collections - 2:
                    # Swap to prefer this one
                    candidates_for_collection[0], candidates_for_collection[i] = candidates_for_collection[i], candidates_for_collection[0]
                    break
            
            # Also ensure cauldrons with 0 collections get priority even if lower threshold
            zero_collections = [c for c in candidates_for_collection if collections_per_cauldron[c[1]] == 0]
            if zero_collections and collections_per_cauldron[candidates_for_collection[0][1]] > 0:
                # If top candidate has collections but there's one with 0, prefer the one with 0
                best_zero = max(zero_collections, key=lambda x: x[0])
                if best_zero[0] >= 50:  # Only if it has reasonable priority
                    candidates_for_collection.insert(0, best_zero)
                    candidates_for_collection = [c for c in candidates_for_collection if c != best_zero or candidates_for_collection.index(c) == 0]
    
    if candidates_for_collection:
        priority, cauldron_id, level = candidates_for_collection[0]
        if cauldron_id not in cauldrons_needing_collection:
            max_vol = cauldrons[cauldron_id]['max_volume']
            shift = get_witch_shift(current_time)
            available_witches = witches_by_shift[shift]
            
            witch_id = None
            for w in available_witches:
                travel_to = get_travel_time('market_001', cauldron_id)
                collection_duration = random.randint(60, 90)  # Increased to 60-90 minutes (longer collections)
                travel_back = get_travel_time(cauldron_id, 'market_001')
                
                # Calculate earliest departure time (must be after previous trip ends + buffer)
                earliest_departure = current_time
                if w in witch_schedules and len(witch_schedules[w]) > 0:
                    # Find the latest trip for this witch
                    latest_trip = max(witch_schedules[w], key=lambda x: x.get('unload_complete') or datetime.min)
                    last_unload = latest_trip.get('unload_complete')
                    if last_unload:
                        # Need buffer time after unload before next departure
                        earliest_departure = max(current_time, last_unload + timedelta(minutes=MIN_BUFFER_BETWEEN_TRIPS))
                
                departure = earliest_departure
                collection_start = departure + timedelta(minutes=travel_to)
                collection_end = collection_start + timedelta(minutes=collection_duration)
                arrival_back = collection_end + timedelta(minutes=travel_back)
                unload_complete = arrival_back + timedelta(minutes=UNLOAD_TIME)
                
                if is_witch_available(w, departure, unload_complete, witch_schedules):
                    witch_id = w
                    
                    # Calculate collection
                    level_at_collection = level + (fill_rates[cauldron_id] * travel_to)
                    level_at_collection = min(level_at_collection, max_vol)
                    
                    # MUCH smaller collection percentage - collect very little each time
                    collection_percentage = random.uniform(0.10, 0.18)  # Reduced from 0.25-0.40 to 0.10-0.18
                    amount_to_collect = min(level_at_collection * collection_percentage, MAX_CAPACITY_PER_WITCH)
                    
                    # Calculate net drain: amount collected is what we take
                    fill_during_collection = fill_rates[cauldron_id] * collection_duration
                    actual_drain = amount_to_collect
                    
                    # Ensure we're actually draining something meaningful (but much smaller amounts)
                    if actual_drain <= fill_during_collection:
                        actual_drain = fill_during_collection + random.uniform(15, 40)  # Reduced from 30-80 to 15-40
                        amount_to_collect = actual_drain
                    
                    # Cap at available level
                    actual_drain = min(actual_drain, level_at_collection)
                    actual_drain = max(10, actual_drain)  # Reduced minimum from 20 to 10
                    
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
                    
                    # Add drain to pending
                    pending_drains.append({
                        'cauldron_id': cauldron_id,
                        'start': collection_start,
                        'end': collection_end,
                        'duration': collection_duration,
                        'net_drain': actual_drain
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
                    
                    transport_tickets.append(ticket)
                    collections_per_cauldron[cauldron_id] += 1
                    cauldrons_needing_collection[cauldron_id] = collection_end
                    
                    break
    
    # Remove completed collections from tracking
    for cauldron_id in list(cauldrons_needing_collection.keys()):
        if current_time >= cauldrons_needing_collection[cauldron_id]:
            del cauldrons_needing_collection[cauldron_id]
    
    # Store this minute's data
    historical_data.append({
        'timestamp': current_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'cauldron_levels': minute_levels.copy()
    })
    
    # Progress indicator
    if len(historical_data) % progress_interval == 0:
        progress = (len(historical_data) / total_minutes) * 100
        print(f"  Progress: {progress:.0f}%")
    
    current_time += timedelta(minutes=1)

# Add unreported drains (10-12 instances across the entire period)
print("\nAdding unreported drains...")
random.seed(54321)

# Generate unreported drains at random times throughout the period
num_unreported = random.randint(10, 12)
for _ in range(num_unreported):
    # Random time within the period
    drain_start = start_date + timedelta(
        minutes=random.randint(0, total_minutes - 200)
    )
    
    # Find level at this time - find closest entry to drain_start
    level_at_time = None
    entry_at_start = None
    min_diff = float('inf')
    for entry in historical_data:
        ts = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
        diff = abs((ts - drain_start).total_seconds())
        if diff < 60 and diff < min_diff:  # Within 1 minute and closest
            level_at_time = entry['cauldron_levels']
            entry_at_start = entry
            min_diff = diff
    
    if level_at_time and entry_at_start:
        # Choose a cauldron with reasonable level
        candidates = [(cid, lvl) for cid, lvl in level_at_time.items() if lvl > 200]
        if candidates:
            cauldron_id, level = random.choice(candidates)
            drain_duration = random.randint(60, 80)
            drain_end = drain_start + timedelta(minutes=drain_duration)
            
            # Unreported drains - ensure significant drain amounts that show visible drops
            fill_rate = fill_rates[cauldron_id]
            
            # Calculate drain amount - ensure it's LARGE enough to show clear visible drops
            fill_during_drain = fill_rate * drain_duration
            
            # Target a MINIMUM net drop of 50-100L (visible on graph)
            # net_drop = (drain_rate - fill_rate) * duration
            # So: drain_rate * duration = net_drop + fill_during_drain
            min_net_drop = random.uniform(50, 100)  # Minimum visible drop
            min_drain_amount = fill_during_drain + min_net_drop
            max_drain = min(level * 0.50, level - 40)
            
            # Generate drain amount (ensures minimum visible drop)
            if min_drain_amount < max_drain:
                drain_amount = random.uniform(min_drain_amount, max_drain)
            else:
                drain_amount = min_drain_amount
            
            # Calculate net drain per minute (this should guarantee visible drop)
            drain_rate_per_min = drain_amount / drain_duration
            net_drain_per_min = drain_rate_per_min - fill_rate
            
            # Final verification - net_drain_per_min should be at least 0.7 L/min
            if net_drain_per_min < 0.7:
                # Force larger drain to ensure visibility
                min_net_drop = 70  # Force at least 70L drop
                drain_amount = fill_during_drain + min_net_drop + random.uniform(20, 60)
                drain_rate_per_min = drain_amount / drain_duration
                net_drain_per_min = drain_rate_per_min - fill_rate
            
            # Sanity check
            expected_total_drop = net_drain_per_min * drain_duration
            if expected_total_drop < 40:
                print(f"⚠️  Warning: Expected drop only {expected_total_drop:.1f}L for {cauldron_id}, increasing...")
                drain_amount = fill_during_drain + 80  # Force 80L minimum drop
                drain_rate_per_min = drain_amount / drain_duration
                net_drain_per_min = drain_rate_per_min - fill_rate
            
            # Apply drain minute by minute during the drain period
            # CRITICAL: Apply drain to ALL entries within the drain period
            drain_count = 0
            for idx, entry in enumerate(historical_data):
                ts = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                # Match entries within drain period (inclusive of start and end)
                if drain_start <= ts <= drain_end:
                    # Get current level for this cauldron
                    if cauldron_id in entry['cauldron_levels']:
                        current_level = entry['cauldron_levels'][cauldron_id]
                        # Apply net drain - subtract net drain per minute
                        # This accounts for the fact that filling already happened, so we just subtract net drain
                        new_level = current_level - net_drain_per_min
                        entry['cauldron_levels'][cauldron_id] = max(0, round(new_level, 2))
                        drain_count += 1
            
            # Verify drain was applied - this is critical
            if drain_count == 0:
                print(f"⚠️  Warning: Unreported drain for {cauldron_id} at {drain_start} wasn't applied!")
            elif drain_count < (drain_duration - 5):  # Should have ~drain_duration entries
                print(f"⚠️  Warning: Only {drain_count} entries modified for drain (expected ~{drain_duration})")
            
            unreported_drains.append({
                'cauldron_id': cauldron_id,
                'drain_start_timestamp': drain_start.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'drain_end_timestamp': drain_end.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'estimated_amount_drained_liters': round(drain_amount, 2),
                'duration_minutes': drain_duration,
                'note': 'NO TICKET EXISTS - this is an unreported drain'
            })

# Prepare output
output_hist = {
    'metadata': {
        'start_date': start_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'end_date': end_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'total_minutes': len(historical_data),
        'total_collections': len(transport_tickets),
        'data_points': len(historical_data)
    },
    'data': historical_data
}

output_tickets = {
    'metadata': {
        'total_tickets': len(transport_tickets),
        'suspicious_tickets': sum(1 for t in transport_tickets if t.get('is_suspicious')),
        'date_range': {
            'start': min(t['collection_start_timestamp'] for t in transport_tickets),
            'end': max(t['collection_start_timestamp'] for t in transport_tickets)
        }
    },
    'transport_tickets': transport_tickets
}

output_drains = {
    'metadata': {
        'total_unreported_drains': len(unreported_drains),
        'date_range': {
            'start': min(d['drain_start_timestamp'] for d in unreported_drains),
            'end': max(d['drain_start_timestamp'] for d in unreported_drains)
        }
    },
    'unreported_drains': unreported_drains
}

# Save files
print("\nSaving files...")
with open('historical_data.json', 'w') as f:
    json.dump(output_hist, f, indent=2)

with open('transport_tickets.json', 'w') as f:
    json.dump(output_tickets, f, indent=2)

with open('unreported_drains.json', 'w') as f:
    json.dump(output_drains, f, indent=2)

print("\n" + "=" * 70)
print("✅ Data regeneration complete!")
print("=" * 70)
print(f"   Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
print(f"   Total minutes: {len(historical_data):,}")
print(f"   Transport tickets: {len(transport_tickets)}")
print(f"   Unreported drains: {len(unreported_drains)}")
print(f"   Suspicious tickets: {sum(1 for t in transport_tickets if t.get('is_suspicious'))}")

print(f"\nTicket distribution:")
for cid in sorted(collections_per_cauldron.keys()):
    print(f"   {cid}: {collections_per_cauldron[cid]}")

