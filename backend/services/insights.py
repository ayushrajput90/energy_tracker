"""
Smart Data-Driven Insights Engine
Generates actionable, rule-based insights and recommendations based on user energy records and goals.
"""
from datetime import date, timedelta
from backend.models.energy_record import EnergyRecord
from backend.models.goal import Goal
from backend.services.aggregation import aggregate_by_source
from backend.services.calculations import aggregate_record_list

def generate_insights(user_id: int, emission_factor: float = 0.82, default_tariff: float = 0.15) -> list:
    insights = []
    today = date.today()

    # 1. Fetch all records for the user
    all_records = EnergyRecord.query.filter_by(user_id=user_id).all()
    if not all_records:
        return [{
            'type': 'welcome',
            'icon': 'sparkles',
            'category': 'Getting Started',
            'title': 'Welcome to Renewable Energy Usage Tracker!',
            'message': 'Add your first energy records across Solar, Wind, Hydro, or other sources to start generating data-driven insights.',
            'badge': 'Starter Tip',
            'priority': 1
        }]

    # 2. Overall aggregation
    overall_agg = aggregate_record_list(all_records, emission_factor, default_tariff)
    total_gen = overall_agg['total_generated_kwh']
    ren_pct = overall_agg['renewable_percentage']
    co2_avoided = overall_agg['estimated_co2_avoided_kg']
    savings = overall_agg['estimated_cost_savings']

    # 3. Source Breakdown Analysis
    sources_data = aggregate_by_source(all_records, emission_factor, default_tariff)
    active_sources = [s for s in sources_data.values() if s['total_generated_kwh'] > 0]
    
    if active_sources:
        active_sources.sort(key=lambda x: x['total_generated_kwh'], reverse=True)
        top_source = active_sources[0]
        insights.append({
            'type': 'top_source',
            'icon': 'sun',
            'category': 'Source Performance',
            'title': f'{top_source["source"]} is your #1 Energy Producer',
            'message': f'{top_source["source"]} generated {top_source["total_generated_kwh"]:.1f} kWh, contributing {top_source["contribution_percentage"]:.1f}% of your total renewable energy production.',
            'badge': 'Dominant Source',
            'priority': 1
        })

    # 4. Period Comparison: This Month vs Last Month
    start_this_month = today.replace(day=1)
    last_month_end = start_this_month - timedelta(days=1)
    start_last_month = last_month_end.replace(day=1)

    this_month_records = [r for r in all_records if r.date >= start_this_month]
    last_month_records = [r for r in all_records if start_last_month <= r.date <= last_month_end]

    this_month_agg = aggregate_record_list(this_month_records, emission_factor, default_tariff)
    last_month_agg = aggregate_record_list(last_month_records, emission_factor, default_tariff)

    if last_month_agg['total_generated_kwh'] > 0 and this_month_agg['total_generated_kwh'] > 0:
        diff_gen = this_month_agg['total_generated_kwh'] - last_month_agg['total_generated_kwh']
        pct_change = (diff_gen / last_month_agg['total_generated_kwh']) * 100.0
        if pct_change > 0:
            insights.append({
                'type': 'trend_positive',
                'icon': 'trending-up',
                'category': 'Monthly Growth',
                'title': f'Renewable Generation Increased by {pct_change:.1f}%',
                'message': f'You generated {this_month_agg["total_generated_kwh"]:.1f} kWh this month compared to {last_month_agg["total_generated_kwh"]:.1f} kWh last month.',
                'badge': 'Positive Trend',
                'priority': 2
            })
        elif pct_change < -5:
            insights.append({
                'type': 'trend_warning',
                'icon': 'trending-down',
                'category': 'Monthly Dip',
                'title': f'Renewable Generation Decreased by {abs(pct_change):.1f}%',
                'message': 'Consider checking equipment performance or weather factors to optimize generation output.',
                'badge': 'Performance Alert',
                'priority': 2
            })

    # 5. Renewable Percentage Milestones
    if ren_pct >= 80:
        insights.append({
            'type': 'milestone',
            'icon': 'award',
            'category': 'Green Champion',
            'title': f'Exceptional {ren_pct:.1f}% Clean Energy Reliance',
            'message': 'Over 80% of your total electricity consumption is powered by clean renewable sources, drastically minimizing grid reliance.',
            'badge': 'High Efficiency',
            'priority': 2
        })
    elif ren_pct >= 50:
        insights.append({
            'type': 'milestone',
            'icon': 'check-circle',
            'category': 'Clean Transition',
            'title': f'Clean Energy Majority ({ren_pct:.1f}%)',
            'message': 'More than half of your power demand is satisfied through your renewable assets.',
            'badge': 'Milestone Reached',
            'priority': 3
        })
    else:
        insights.append({
            'type': 'opportunity',
            'icon': 'zap',
            'category': 'Optimization',
            'title': 'Opportunity to Boost Renewable Share',
            'message': f'Your current renewable share is {ren_pct:.1f}%. Increasing renewable generation or shifting high-load tasks to peak generation hours will cut grid consumption.',
            'badge': 'Action Item',
            'priority': 3
        })

    # 6. Environmental Impact Real-World Equivalencies
    if co2_avoided > 0:
        trees_equivalent = round(co2_avoided / 21.77, 1) # Approx 21.77 kg CO2 absorbed by one urban tree per year
        car_miles_avoided = round(co2_avoided * 2.5, 1) # Approx 0.404 kg CO2 / mile
        insights.append({
            'type': 'environmental',
            'icon': 'leaf',
            'category': 'Carbon Footprint',
            'title': f'{co2_avoided:.1f} kg CO2 Emissions Avoided',
            'message': f'Your clean energy production equals the carbon absorption of approximately {trees_equivalent} trees in a year or displacing ~{car_miles_avoided} miles of gasoline driving.',
            'badge': 'Eco Impact',
            'priority': 2
        })

    # 7. Financial Savings Highlight
    if savings > 0:
        insights.append({
            'type': 'financial',
            'icon': 'dollar-sign',
            'category': 'Cost Savings',
            'title': f'Estimated ${savings:.2f} Saved on Electricity',
            'message': f'By displacing grid power with {overall_agg["total_renewable_consumed_kwh"]:.1f} kWh of renewable power, you have reduced utility bills.',
            'badge': 'Cost Reduction',
            'priority': 3
        })

    # 8. Active Goals Proximity Check
    active_goals = Goal.query.filter_by(user_id=user_id, status='Active').all()
    for g in active_goals:
        # Check current progress
        goal_records = [r for r in all_records if g.start_date <= r.date <= g.end_date]
        g_agg = aggregate_record_list(goal_records, emission_factor, default_tariff)
        
        current_val = 0.0
        if g.goal_type == 'Energy Generation':
            current_val = g_agg['total_generated_kwh']
        elif g.goal_type == 'Renewable Consumption':
            current_val = g_agg['total_renewable_consumed_kwh']
        elif g.goal_type == 'Renewable Percentage':
            current_val = g_agg['renewable_percentage']
        elif g.goal_type == 'CO2 Reduction/Avoidance':
            current_val = g_agg['estimated_co2_avoided_kg']
        elif g.goal_type == 'Grid Electricity Displacement':
            current_val = g_agg['estimated_grid_displaced_kwh']
        elif g.goal_type == 'Cost Savings':
            current_val = g_agg['estimated_cost_savings']

        progress_pct = (current_val / g.target_value * 100.0) if g.target_value > 0 else 0.0
        
        if progress_pct >= 100.0:
            insights.append({
                'type': 'goal_achieved',
                'icon': 'check-circle-2',
                'category': 'Goal Accomplishment',
                'title': f'Goal Achieved: {g.goal_type}!',
                'message': f'Congratulations! You reached {current_val:.1f} of your {g.target_value:.1f} target for "{g.description or g.goal_type}".',
                'badge': '100% Completed',
                'priority': 1
            })
        elif progress_pct >= 75.0:
            insights.append({
                'type': 'goal_progress',
                'icon': 'target',
                'category': 'Goal in Reach',
                'title': f'Almost There: {g.goal_type}',
                'message': f'You are at {progress_pct:.1f}% ({current_val:.1f}/{g.target_value:.1f}) towards your target before {g.end_date}.',
                'badge': f'{progress_pct:.0f}% Done',
                'priority': 2
            })

    # Sort insights by priority
    insights.sort(key=lambda x: x.get('priority', 99))
    return insights
