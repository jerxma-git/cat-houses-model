def extract_avg_total_time(stats):
    return sum(stat["total_execution_time"] for stat in stats) / len(stats)
def extract_avg_houses_for_sale(stats):
    return sum(stat["for_sale"] for stat in stats) / len(stats)
def extract_avg_houses_for_utilization(stats):
    return sum(stat["for_utilization"] for stat in stats) / len(stats)
def extract_avg_planned_houses(stats):
    return sum(stat["planned_houses_num"] for stat in stats) / len(stats)

def extract_base_metrics(stats):
    return {
        'total_time':extract_avg_total_time(stats),
        'for_sale': extract_avg_houses_for_sale(stats),
        'for_utilization': extract_avg_houses_for_utilization(stats),
        'planned_houses_num': extract_avg_planned_houses(stats)
    }

def extract_business_metrics(stats):
    base_metrics = extract_base_metrics(stats)
    return {
        'houses_per_time': base_metrics['for_sale'] / base_metrics['total_time'],
        'house_success_rate': base_metrics['for_sale'] / base_metrics['planned_houses_num'],
        'cat_approval_rate': base_metrics['for_sale'] / (base_metrics['for_sale'] + base_metrics['for_utilization'])
    }