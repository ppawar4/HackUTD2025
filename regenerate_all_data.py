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

# Fill rates - Increased by ~35% to boost production
# Creates variation: some slow, some moderate, some fast
fill_rates = {
    # Non-009 cauldrons: Very low fill rates to prevent overflow - rely on frequent collections
    'cauldron_001': 0.08,   # Very low to prevent overflow
    'cauldron_002': 0.065,  # Very low to prevent overflow
    'cauldron_003': 0.09,   # Very low to prevent overflow
    'cauldron_004': 0.07,   # Very low to prevent overflow
    'cauldron_005': 0.075,  # Very low to prevent overflow
    'cauldron_006': 0.055,  # Very low to prevent overflow
    'cauldron_007': 0.095,  # Very low to prevent overflow
    'cauldron_008': 0.08,   # Very low to prevent overflow
    'cauldron_009': 0.18,   # Higher fill rate - will overflow around midpoint (~50% of period)
    'cauldron_010': 0.075,  # Very low to prevent overflow
    'cauldron_011': 0.09,   # Very low to prevent overflow
    'cauldron_012': 0.065,  # Very low to prevent overflow
}

# Collection thresholds (percentage of max volume) - EXTREMELY aggressive for all except 009
# Very low thresholds to trigger frequent collections - prevent overflow for all except 009
collection_thresholds = {
    'cauldron_001': 0.015, 'cauldron_002': 0.018, 'cauldron_003': 0.018,
    'cauldron_004': 0.015, 'cauldron_005': 0.018, 'cauldron_006': 0.020,
    'cauldron_007': 0.015, 'cauldron_008': 0.018, 'cauldron_009': 0.12,  # Higher threshold - allow overflow around midpoint
    'cauldron_010': 0.020, 'cauldron_011': 0.015, 'cauldron_012': 0.018,
}

# Constants
UNLOAD_TIME = 15
MAX_CAPACITY_PER_WITCH = 70  # Reduced to 70L per witch
MIN_BUFFER_BETWEEN_TRIPS = 30  # Minimum minutes between trips (from unload complete to next departure)
# NOTE: We now use CONSTANT NET drain rate instead of constant gross drain rate
# This ensures consistent drain rates across all cauldrons regardless of fill rate
CONSTANT_NET_DRAIN_RATE_L_PER_HOUR = 24.0  # Constant NET drain rate: 24 L/hour
CONSTANT_NET_DRAIN_RATE_L_PER_MIN = CONSTANT_NET_DRAIN_RATE_L_PER_HOUR / 60.0  # 0.4 L/min

# Legacy constant for backward compatibility (not used in new logic)
CONSTANT_DRAIN_RATE_L_PER_HOUR = 50.0  # Not used - kept for reference
CONSTANT_DRAIN_RATE_L_PER_MIN = CONSTANT_DRAIN_RATE_L_PER_HOUR / 60.0  # Not used

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

def is_witch_available(witch_id, start_time, end_time, witch_schedules, cauldron_id=None, period_progress=None):
    """Check if witch is available for the entire period, including buffer time"""
    if witch_id not in witch_schedules:
        return True
    
    # Use smaller buffer for cauldron_009 before midpoint to allow more frequent collections
    buffer_minutes = MIN_BUFFER_BETWEEN_TRIPS
    if cauldron_id == 'cauldron_009' and period_progress is not None and period_progress < 0.50:
        buffer_minutes = 15  # Reduced buffer for urgent collections
    
    # Add buffer before start and after end to ensure adequate spacing
    buffer_start = start_time - timedelta(minutes=buffer_minutes)
    buffer_end = end_time + timedelta(minutes=buffer_minutes)
    
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
    if cauldron_id == 'cauldron_009':
        # Start cauldron_009 at extremely low level so it hits capacity around midpoint
        # With fill rate 0.35 L/min and 10 days to midpoint, start very low
        # Start at 0.1-0.3% to maximize delay until midpoint
        initial_levels[cauldron_id] = random.uniform(max_vol * 0.001, max_vol * 0.003)
    else:
        # Start at 20-40% of capacity
        initial_levels[cauldron_id] = random.uniform(max_vol * 0.20, max_vol * 0.40)

print(f"Initial levels: {initial_levels}")

# Data structures
historical_data = []
transport_tickets = []

# Load existing unreported drains if they exist
unreported_drains = []
try:
    with open('unreported_drains.json', 'r') as f:
        existing_unreported = json.load(f)
        unreported_drains = existing_unreported.get('unreported_drains', [])
        if unreported_drains:
            print(f"Loaded {len(unreported_drains)} existing unreported drains")
except FileNotFoundError:
    print("No existing unreported_drains.json found, will generate new ones")
    unreported_drains = []

witch_schedules = defaultdict(list)
pending_drains = []  # Active drains
cauldrons_needing_collection = {}
collections_per_cauldron = defaultdict(int)
ticket_counter = 0

# Add existing unreported drains to pending_drains
for drain_info in unreported_drains:
    drain_start = datetime.fromisoformat(drain_info['drain_start_timestamp'].replace('Z', '+00:00'))
    drain_end = datetime.fromisoformat(drain_info['drain_end_timestamp'].replace('Z', '+00:00'))
    duration_minutes = drain_info.get('duration_minutes', int((drain_end - drain_start).total_seconds() / 60))
    drain_amount = drain_info.get('estimated_amount_drained_liters', 0)
    
    # Calculate net drain (accounting for fill during drain)
    fill_rate = fill_rates.get(drain_info['cauldron_id'], 0)
    fill_during_drain = fill_rate * duration_minutes
    net_drain = drain_amount  # drain_amount is already the net amount
    
    pending_drains.append({
        'cauldron_id': drain_info['cauldron_id'],
        'start': drain_start,
        'end': drain_end,
        'duration': duration_minutes,
        'net_drain': net_drain
    })

current_levels = {k: v for k, v in initial_levels.items()}
current_time = start_date
random.seed(12345)  # For reproducibility

print("\nGenerating data...")
progress_interval = total_minutes // 10

while current_time <= end_date:
    # Start with current levels
    minute_levels = current_levels.copy()
    
    # Check which cauldrons are currently being drained (to prevent filling during drain)
    cauldrons_being_drained = set()
    for drain in pending_drains:
        if drain['start'] <= current_time <= drain['end']:
            cauldrons_being_drained.add(drain['cauldron_id'])
    
    # Update levels with filling FIRST (WITH SLIGHTLY MORE NOISE)
    for cauldron_id, current_level in minute_levels.items():
        max_vol = cauldrons[cauldron_id]['max_volume']
        fill_rate = fill_rates[cauldron_id]
        # Fill rate is constant for each cauldron throughout the entire period
        
        # CRITICAL: During active drains, we still fill but the drain accounts for it
        # The net_drain_per_min already accounts for filling, so we need to use gross drain rate
        # OR: Don't fill during drain and use net drain rate
        # Let's use the simpler approach: don't fill during drain, drain uses net rate
        
        # Check if this cauldron is currently being drained
        is_currently_draining = cauldron_id in cauldrons_being_drained
        
        if is_currently_draining:
            # During drain: Don't fill - the drain will account for continuous filling
            # The net_drain_per_min already accounts for fill rate
            new_level = current_level
        else:
            # Normal filling when not draining
            # Apply noise: 98% to 102% (2% variation) - cleaner data
            base_noise_factor = random.uniform(0.98, 1.02)
            
            # Occasional larger variations (1% chance)
            if random.random() < 0.01:
                spike_factor = random.uniform(0.97, 1.03)  # Smaller variation occasionally
            else:
                spike_factor = 1.0
            
            noise_factor = base_noise_factor * spike_factor
            fill_amount = fill_rate * noise_factor
            
            # Jitter (±0.05% of current level) - cleaner data
            jitter = random.uniform(-0.0005, 0.0005) * current_level
            
            # Normal filling - cap at max_vol
            new_level = min(current_level + fill_amount + jitter, max_vol)
        
        # Ensure level doesn't go negative
        new_level = max(0, new_level)
        
        minute_levels[cauldron_id] = round(new_level, 2)
        current_levels[cauldron_id] = new_level
    
    # THEN apply any active drains (AFTER filling, so drain accounts for simultaneous filling)
    # CRITICAL: Drains must always reduce levels, even when at capacity
    # The net drain per minute already accounts for filling during the drain period
    for drain in list(pending_drains):
        # Check if current_time is within drain period
        if drain['start'] <= current_time <= drain['end']:
            # Apply drain - calculate net drain per minute
            net_drain = drain.get('net_drain', 0)
            if drain['duration'] > 0 and net_drain > 0:
                net_drain_per_min = net_drain / drain['duration']
                current_cauldron_level = minute_levels[drain['cauldron_id']]
                
                # CRITICAL: Always reduce level by net drain per minute
                # net_drain_per_min = (drain_rate - fill_rate) per minute
                # So subtracting it accounts for both draining AND filling during this minute
                new_level = current_cauldron_level - net_drain_per_min
                
                # Ensure level doesn't go negative
                new_level = max(0, new_level)
                
                # Ensure the level actually decreased (for debugging)
                if current_cauldron_level >= cauldrons[drain['cauldron_id']]['max_volume'] * 0.99:
                    # If at capacity, the level MUST decrease
                    if new_level >= current_cauldron_level:
                        # This shouldn't happen - net_drain_per_min should always be positive
                        # But if it does, force a reduction
                        new_level = current_cauldron_level - max(net_drain_per_min, 0.1)
                        new_level = max(0, new_level)
                
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
            elif has_no_collections and level >= max_vol * 0.45:  # Increased from 0.40
                priority = 70
            elif has_no_collections and level >= max_vol * 0.35:  # Increased from 0.30
                priority = 65
            # Lower priority but still collect if below threshold but no collections yet
            elif collections_per_cauldron[cauldron_id] == 0 and level >= max_vol * 0.30:  # Increased from 0.25
                priority = 60
            # Additional triggers - VERY aggressive for all cauldrons EXCEPT 009
            # cauldron_009 should overflow, but ONLY after the midpoint (~50% of period)
            # Calculate what fraction of the period we're in (0.0 = start, 1.0 = end)
            period_progress = (current_time - start_date).total_seconds() / (end_date - start_date).total_seconds()
            is_after_midpoint = period_progress >= 0.50  # After midpoint (50%)
            
            if cauldron_id == 'cauldron_009':
                if is_after_midpoint:
                    # After midpoint: Allow overflow - moderate triggers
                    if level >= max_vol * 0.60:  # 60% full - trigger collection
                        priority = 88
                    elif level >= max_vol * 0.55:  # 55% full - trigger collection
                        priority = 83
                    elif level >= max_vol * 0.50:  # 50% full - trigger collection
                        priority = 78
                else:
                    # Before midpoint: EXTREMELY aggressive to prevent overflow until midpoint
                    # Collect at VERY low levels to keep it from filling up
                    # Make collections so frequent that it never gets above 3% before midpoint
                    if level >= max_vol * 0.03:  # 3% full - trigger collection immediately (CRITICAL)
                        priority = 99
                    elif level >= max_vol * 0.025:  # 2.5% full - trigger collection
                        priority = 98
                    elif level >= max_vol * 0.02:  # 2% full - trigger collection
                        priority = 97
                    elif level >= max_vol * 0.015:  # 1.5% full - trigger collection
                        priority = 96
                    elif level >= max_vol * 0.01:  # 1% full - trigger collection
                        priority = 95
                    elif level >= max_vol * 0.008:  # 0.8% full - trigger collection
                        priority = 94
                    elif level >= max_vol * 0.005:  # 0.5% full - trigger collection
                        priority = 93
            else:
                # EXTREMELY aggressive triggers for ALL other cauldrons to PREVENT overflow
                # Only cauldron_009 should overflow - all others must NEVER overflow
                # Trigger collections at VERY low levels to prevent any overflow
                if level >= max_vol * 0.025:  # 2.5% full - trigger collection immediately (CRITICAL)
                    priority = 99
                elif level >= max_vol * 0.02:  # 2% full - trigger collection
                    priority = 98
                elif level >= max_vol * 0.015:  # 1.5% full - trigger collection
                    priority = 97
                elif level >= max_vol * 0.01:  # 1% full - trigger collection
                    priority = 96
                elif level >= max_vol * 0.008:  # 0.8% full - trigger collection
                    priority = 95
                elif level >= max_vol * 0.005:  # 0.5% full - trigger collection
                    priority = 94
                elif level >= max_vol * 0.003:  # 0.3% full - trigger collection
                    priority = 93
            
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
                if best_zero[0] >= 60:  # Increased from 50 - only if it has higher priority
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
                
                # Calculate collection amount first (using estimated duration)
                level_at_collection = level + (fill_rates[cauldron_id] * travel_to)
                level_at_collection = min(level_at_collection, max_vol)
                
                # Collection percentage - adjusted to collect more per trip (reduces total trips)
                # For cauldron_009 before midpoint, collect more aggressively to prevent overflow
                period_progress_collection = (current_time - start_date).total_seconds() / (end_date - start_date).total_seconds()
                is_after_midpoint_collection = period_progress_collection >= 0.50
                
                if cauldron_id == 'cauldron_009' and not is_after_midpoint_collection:
                    collection_percentage = random.uniform(0.50, 0.60)  # Collect even more before midpoint
                else:
                    # Collect more per trip to prevent overflow
                    # For non-009 cauldrons, collect very aggressively to prevent any overflow
                    if cauldron_id != 'cauldron_009':
                        collection_percentage = random.uniform(0.50, 0.60)  # Very aggressive for non-009
                    else:
                        collection_percentage = random.uniform(0.35, 0.45)  # Normal for 009
                amount_to_collect = min(level_at_collection * collection_percentage, MAX_CAPACITY_PER_WITCH)
                
                # Estimate initial duration for calculation
                estimated_duration = random.randint(60, 90)
                fill_during_estimated = fill_rates[cauldron_id] * estimated_duration
                actual_drain = amount_to_collect
                
                # Ensure we're actually draining something meaningful (but much smaller amounts)
                if actual_drain <= fill_during_estimated:
                    actual_drain = fill_during_estimated + random.uniform(15, 40)  # Reduced from 30-80 to 15-40
                    amount_to_collect = actual_drain
                
                # Cap at available level AND witch capacity
                actual_drain = min(actual_drain, level_at_collection, MAX_CAPACITY_PER_WITCH)
                actual_drain = max(15, actual_drain)  # Increased minimum from 10 to 15
                
                # CRITICAL: actual_drain is now FIXED - this is the NET amount that will be drained
                # Duration will be calculated based on this amount, accounting for filling during collection
                
                # Calculate duration based on drain amount: higher volume = longer duration
                # We need to account for filling during collection:
                #   actual_drain = gross_drain - fill_during_collection
                #   gross_drain = collection_rate * duration
                #   fill_during_collection = fill_rate * duration
                #   So: actual_drain = (collection_rate - fill_rate) * duration
                #   Solving: duration = actual_drain / (collection_rate - fill_rate)
                # But we also want a base duration for setup/preparation
                
                fill_rate = fill_rates[cauldron_id]
                # Fill rate is constant for each cauldron throughout the entire period
                
                # Use CONSTANT NET drain rate across all cauldrons
                # This ensures levels decrease at the same rate regardless of fill rate
                # We want a constant NET drain rate, so gross drain rate adjusts to fill rate
                CONSTANT_NET_DRAIN_RATE_L_PER_MIN = 0.400  # Constant net drain: 24 L/hour
                
                # Calculate gross drain rate needed to achieve constant net drain
                # net_drain = gross_drain - fill_during_collection
                # If we want constant net_drain_rate, then:
                #   gross_drain_rate = net_drain_rate + fill_rate
                gross_drain_rate = CONSTANT_NET_DRAIN_RATE_L_PER_MIN + fill_rate
                
                # Duration calculation:
                #   actual_drain = gross_drain - fill_during_collection
                #   gross_drain = gross_drain_rate * duration
                #   fill_during_collection = fill_rate * duration
                #   So: actual_drain = (gross_drain_rate - fill_rate) * duration = net_drain_rate * duration
                #   Solving: duration = actual_drain / net_drain_rate
                
                net_drain_rate = CONSTANT_NET_DRAIN_RATE_L_PER_MIN  # Now constant!
                if net_drain_rate > 0:
                    # Duration from actual drain amount (using constant net drain rate)
                    collection_duration = int(actual_drain / net_drain_rate)
                else:
                    # Fallback if net drain rate is somehow zero or negative
                    collection_duration = int(actual_drain / 0.1)  # Use 0.1 L/min as fallback
                
                # Clamp duration to reasonable bounds (15-180 minutes)
                collection_duration = max(15, min(180, collection_duration))
                
                # Recalculate fill during collection with actual duration
                fill_during_collection = fill_rate * collection_duration
                
                # Verify: With constant net drain rate:
                #   actual_drain = net_drain_rate * duration = CONSTANT_NET_DRAIN_RATE * duration
                #   gross_drain = actual_drain + fill_during_collection
                # This ensures the levels will drop by exactly actual_drain over the duration
                
                # Recalculate with actual duration
                collection_end = collection_start + timedelta(minutes=collection_duration)
                arrival_back = collection_end + timedelta(minutes=travel_back)
                unload_complete = arrival_back + timedelta(minutes=UNLOAD_TIME)
                
                period_progress_availability = (current_time - start_date).total_seconds() / (end_date - start_date).total_seconds()
                if is_witch_available(w, departure, unload_complete, witch_schedules, cauldron_id, period_progress_availability):
                    witch_id = w
                    
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
                    reported_amount = actual_drain  # Based on fixed actual_drain amount
                    
                    if is_suspicious:
                        underreport_factor = random.uniform(0.75, 0.92)
                        reported_amount = actual_drain * underreport_factor
                    
                    # Create ticket
                    # NOTE: Only collection_start_timestamp and collection_timestamp change with duration
                    # amount_collected is based on actual_drain which remains fixed
                    ticket_counter += 1
                    date_str = collection_start.strftime('%Y%m%d')
                    ticket_id = f"TT_{date_str}_{ticket_counter:03d}"
                    
                    ticket = {
                        'ticket_id': ticket_id,
                        'cauldron_id': cauldron_id,
                        'collection_start_timestamp': collection_start.strftime('%Y-%m-%dT%H:%M:%SZ'),
                        'collection_timestamp': collection_end.strftime('%Y-%m-%dT%H:%M:%SZ'),  # Updated based on new duration
                        'amount_collected': round(reported_amount, 2),  # Based on fixed actual_drain
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
# Skip if we already loaded existing unreported drains
existing_unreported_count = len([d for d in unreported_drains if 'drain_start_timestamp' in d])
if existing_unreported_count > 0:
    print(f"\nSkipping unreported drain generation - using {existing_unreported_count} existing drains")
    added_unreported_drains = [d for d in unreported_drains if 'drain_start_timestamp' in d]
    # Keep the loaded drains in unreported_drains
    unreported_drains = added_unreported_drains
else:
    print("\nAdding unreported drains...")
    added_unreported_drains = []
    random.seed(54321)

        # Get all ticket times to avoid overlaps
    ticket_times = []
    for ticket in transport_tickets:
        start = datetime.fromisoformat(ticket['collection_start_timestamp'].replace('Z', '+00:00'))
        end = datetime.fromisoformat(ticket['collection_timestamp'].replace('Z', '+00:00'))
        ticket_times.append((start, end))

    def overlaps_with_tickets(drain_start, drain_end):
        """Check if drain overlaps with any ticket times"""
        # Only check direct overlap, no buffer - unreported drains can happen near tickets
        for ticket_start, ticket_end in ticket_times:
            if not (drain_end <= ticket_start or drain_start >= ticket_end):
                return True
        return False

    # Generate unreported drains at random times throughout the period
    num_unreported = random.randint(10, 12)
    attempts = 0
    max_attempts = 1000  # Increased significantly

    # Track all unreported drains to ensure spacing
    added_unreported_drains = []

    # Find time gaps where no tickets are happening
    # Sample times throughout the period and check for gaps
    gap_times = []
    for _ in range(100):  # Sample 100 random times
        sample_time = start_date + timedelta(minutes=random.randint(200, total_minutes - 200))
        # Check if this time is in a gap (not overlapping with any ticket)
        is_gap = True
        for ticket_start, ticket_end in ticket_times:
            if ticket_start <= sample_time <= ticket_end:
                is_gap = False
                break
        if is_gap:
            gap_times.append(sample_time)

    # If we found gaps, use them; otherwise fall back to random
    use_gaps = len(gap_times) > 0

    while len(added_unreported_drains) < num_unreported:
        attempts += 1
        if attempts > max_attempts:
            print(f"⚠️  Warning: Could not generate all {num_unreported} unreported drains after {max_attempts} attempts. Generated {len(added_unreported_drains)} drains.")
            break
    
        # Use gap times if available, otherwise random
        if use_gaps and len(gap_times) > 0:
            drain_start = random.choice(gap_times)
            gap_times.remove(drain_start)  # Remove so we don't use it again
        else:
            # Random time within the period
            drain_start = start_date + timedelta(
                minutes=random.randint(200, total_minutes - 200)
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
            
                # Check spacing from existing unreported drains for THIS cauldron
                # Need at least 2 hours between drains for same cauldron to allow visible level increase
                # TEMPORARILY DISABLED for debugging - only check if we have some drains already
                too_close_same_cauldron = False
                if len(added_unreported_drains) > 0:  # Only check spacing if we have existing drains
                    for existing_drain in added_unreported_drains:
                        if existing_drain['cauldron_id'] == cauldron_id:
                            existing_start = datetime.fromisoformat(existing_drain['drain_start_timestamp'].replace('Z', '+00:00'))
                            existing_end = datetime.fromisoformat(existing_drain['drain_end_timestamp'].replace('Z', '+00:00'))
                        
                            # Need at least 2 hours between drains for same cauldron to allow visible level increase
                            time_diff_start = abs((drain_start - existing_start).total_seconds() / 3600)  # hours
                            time_diff_end = abs((drain_start - existing_end).total_seconds() / 3600)  # hours
                        
                            if time_diff_start < 2.0 or time_diff_end < 2.0:
                                too_close_same_cauldron = True
                                break
            
                if too_close_same_cauldron:
                    continue  # Skip this attempt and try again
            
                # Also check spacing from other cauldrons (at least 1 hour)
                # TEMPORARILY DISABLED for debugging - only check if we have some drains already
                too_close_other = False
                if len(added_unreported_drains) > 0:  # Only check spacing if we have existing drains
                    for existing_drain in added_unreported_drains:
                        if existing_drain['cauldron_id'] != cauldron_id:
                            existing_start = datetime.fromisoformat(existing_drain['drain_start_timestamp'].replace('Z', '+00:00'))
                            existing_end = datetime.fromisoformat(existing_drain['drain_end_timestamp'].replace('Z', '+00:00'))
                        
                            time_diff_start = abs((drain_start - existing_start).total_seconds() / 3600)  # hours
                            time_diff_end = abs((drain_start - existing_end).total_seconds() / 3600)  # hours
                        
                            if time_diff_start < 1.0 or time_diff_end < 1.0:
                                too_close_other = True
                                break
            
                if too_close_other:
                    continue  # Skip this attempt and try again
            
                # Unreported drains - ensure significant drain amounts that show visible drops
                fill_rate = fill_rates[cauldron_id]
            
                # Calculate NET drain amount first (what will show as a drop)
                # Target a MINIMUM net drop of 15-70L (capped at witch capacity)
                min_net_drop = random.uniform(15, 50)  # Reduced range
                max_drain = min(level * 0.50, level - 15, MAX_CAPACITY_PER_WITCH)  # Cap at witch capacity
            
                # Generate NET drain amount (ensures minimum visible drop)
                # We want at least min_net_drop as the net amount
                if min_net_drop < max_drain:
                    drain_amount = random.uniform(min_net_drop, max_drain)
                else:
                    drain_amount = min(min_net_drop, MAX_CAPACITY_PER_WITCH)
            
                # Cap at witch capacity
                drain_amount = min(drain_amount, MAX_CAPACITY_PER_WITCH)
            
                # Use CONSTANT NET drain rate (same for all cauldrons)
                # Calculate duration using constant net drain rate
                net_drain_rate = CONSTANT_NET_DRAIN_RATE_L_PER_MIN  # Constant across all cauldrons
                if net_drain_rate > 0:
                    # Duration from net drain amount (using constant net drain rate)
                    drain_duration = int(drain_amount / net_drain_rate)
                else:
                    # Fallback if net drain rate is somehow zero or negative
                    drain_duration = int(drain_amount / 0.1)  # Use 0.1 L/min as fallback
            
                # Clamp duration to reasonable bounds (15-180 minutes)
                drain_duration = max(15, min(180, drain_duration))
            
                drain_end = drain_start + timedelta(minutes=drain_duration)
            
                # Skip if overlaps with tickets (direct overlap only, not near tickets)
                # Allow drains to happen near tickets, just not during them
                if overlaps_with_tickets(drain_start, drain_end):
                    continue  # Only skip if directly overlapping
            
                # Recalculate fill_during_drain with actual duration
                fill_during_drain = fill_rate * drain_duration
            
                # Calculate net drain per minute (for applying to historical data)
                net_drain_per_min = drain_amount / drain_duration if drain_duration > 0 else 0
            
                # Final verification - net_drain_per_min should be at least 0.3 L/min
                if net_drain_per_min < 0.3:
                    # Force larger NET drain to ensure visibility (but cap at witch capacity)
                    min_net_drop = 30
                    drain_amount = min(min_net_drop + random.uniform(10, 30), MAX_CAPACITY_PER_WITCH)
                    # Recalculate duration with new drain amount using constant net drain rate
                    net_drain_rate = CONSTANT_NET_DRAIN_RATE_L_PER_MIN  # Constant across all cauldrons
                    if net_drain_rate > 0:
                        drain_duration = int(drain_amount / net_drain_rate)
                    else:
                        drain_duration = int(drain_amount / 0.1)
                    drain_duration = max(15, min(180, drain_duration))
                    drain_end = drain_start + timedelta(minutes=drain_duration)
                    fill_during_drain = fill_rate * drain_duration
                    net_drain_per_min = drain_amount / drain_duration if drain_duration > 0 else 0
            
                # Sanity check - reduced minimum
                expected_total_drop = net_drain_per_min * drain_duration
                if expected_total_drop < 25:  # Reduced from 40L
                    continue  # Skip this one if drop is too small
            
                # Get level BEFORE drain starts (for verification) - get from entry just before drain_start
                level_before = None
                for entry in historical_data:
                    ts = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                    if ts < drain_start and abs((ts - drain_start).total_seconds()) < 300:  # Within 5 minutes before
                        level_before = entry['cauldron_levels'].get(cauldron_id)
                        if level_before is not None:
                            break
            
                # Fallback: use level_at_time if we can't find one before
                if level_before is None:
                    level_before = level_at_time.get(cauldron_id)
            
                if level_before is None:
                    continue  # Skip if we can't find level before
            
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
            
                # Verify drain was applied and check level change
                if drain_count == 0:
                    continue  # Skip if drain wasn't applied
            
                # Find level AFTER drain ends - get from entry just after drain_end
                level_after = None
                for entry in historical_data:
                    ts = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                    if ts > drain_end and abs((ts - drain_end).total_seconds()) < 300:  # Within 5 minutes after
                        level_after = entry['cauldron_levels'].get(cauldron_id)
                        if level_after is not None:
                            break
            
                # Fallback: try exact match
                if level_after is None:
                    for entry in historical_data:
                        ts = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                        if abs((ts - drain_end).total_seconds()) < 60:
                            level_after = entry['cauldron_levels'].get(cauldron_id)
                            break
            
                # Verify level actually dropped
                if level_after is not None and level_before is not None:
                    actual_drop = level_before - level_after
                    # Reduced minimum drop to 10L to allow more drains
                    if actual_drop < 10:
                        continue  # Skip if drop is too small
                
                    # Success! Add the drain
                    drain_info = {
                        'cauldron_id': cauldron_id,
                        'drain_start_timestamp': drain_start.strftime('%Y-%m-%dT%H:%M:%SZ'),
                        'drain_end_timestamp': drain_end.strftime('%Y-%m-%dT%H:%M:%SZ'),
                        'estimated_amount_drained_liters': round(drain_amount, 2),
                        'duration_minutes': drain_duration,
                        'note': 'NO TICKET EXISTS - this is an unreported drain'
                    }
                
                    added_unreported_drains.append(drain_info)
                    unreported_drains.append(drain_info)
                    print(f"  ✓ Added unreported drain: {cauldron_id} at {drain_start.strftime('%Y-%m-%d %H:%M')} ({actual_drop:.1f}L drop)")
                else:
                    continue  # Skip if we can't find level before or after

# Prepare output
output_hist = {
    'metadata': {
        'start_date': start_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'end_date': end_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'interval_minutes': 1,
        'fill_rates_l_per_min': fill_rates,  # Fill rates are constant for each cauldron throughout time
        'constant_net_drain_rate_l_per_min': CONSTANT_NET_DRAIN_RATE_L_PER_MIN,  # Same for all cauldrons
        'constant_net_drain_rate_l_per_hour': CONSTANT_NET_DRAIN_RATE_L_PER_HOUR,
        'noise_parameters': {
            'base_noise_range': [0.98, 1.02],
            'spike_chance': 0.01,
            'spike_range': [0.97, 1.03],
            'jitter_factor': 0.0005
        },
        'unit': 'liters'
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
            'start': min(d['drain_start_timestamp'] for d in unreported_drains) if unreported_drains else None,
            'end': max(d['drain_start_timestamp'] for d in unreported_drains) if unreported_drains else None
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

