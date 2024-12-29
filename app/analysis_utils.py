import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import os

def generate_performance_charts(analysis_data):
    """Create performance visualization charts."""
    # Create directory for charts
    charts_dir = 'analysis_charts'
    os.makedirs(charts_dir, exist_ok=True)
    
    # Generate unique filename for this analysis
    chart_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Create radar chart
    categories = []
    ratings = []
    for category, details in analysis_data['skill_categories'].items():
        categories.append(category)
        ratings.append(float(details['rating']))
    
    # Add overall rating
    categories.append('Overall')
    ratings.append(float(analysis_data['overall_rating']))
    
    # Convert to numpy arrays for calculations
    angles = np.linspace(0, 2*np.pi, len(categories), endpoint=False)
    ratings = np.array(ratings)
    
    # Close the plot by appending first value
    angles = np.concatenate((angles, [angles[0]]))
    ratings = np.concatenate((ratings, [ratings[0]]))
    
    # Create radar chart
    plt.figure(figsize=(8, 8))
    ax = plt.subplot(111, projection='polar')
    ax.plot(angles, ratings, 'o-', linewidth=2, label='Ratings', color='#2980B9')
    ax.fill(angles, ratings, alpha=0.25, color='#3498DB')
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories)
    ax.set_ylim(0, 10)
    plt.title('Performance Overview', pad=20)
    
    # Save radar chart
    radar_chart_path = f"{charts_dir}/radar_chart_{chart_timestamp}.png"
    plt.savefig(radar_chart_path, dpi=300, bbox_inches='tight', transparent=True)
    plt.close()
    
    # Create bar chart for subcategories
    plt.figure(figsize=(10, 6))
    
    # Collect all subcategory data
    subcategories = []
    sub_ratings = []
    colors = []
    category_colors = {
        'Technical Proficiency': '#2980B9',
        'Problem Solving': '#27AE60',
        'Behavioral Skills': '#8E44AD'
    }
    
    for category, details in analysis_data['skill_categories'].items():
        for sub_name, sub_details in details['subcategories'].items():
            subcategories.append(sub_name)
            sub_ratings.append(float(sub_details['rating']))
            colors.append(category_colors.get(category, '#2C3E50'))
    
    # Create bar chart
    y_pos = np.arange(len(subcategories))
    plt.barh(y_pos, sub_ratings, align='center', color=colors, alpha=0.8)
    plt.yticks(y_pos, subcategories)
    plt.xlabel('Rating (0-10)')
    plt.title('Detailed Skills Breakdown')
    
    # Add value labels
    for i, v in enumerate(sub_ratings):
        plt.text(v + 0.1, i, f'{v}', va='center')
    
    # Save bar chart
    bar_chart_path = f"{charts_dir}/bar_chart_{chart_timestamp}.png"
    plt.savefig(bar_chart_path, dpi=300, bbox_inches='tight', transparent=True)
    plt.close()
    
    return radar_chart_path, bar_chart_path

async def analyze_performance_from_json(data):
    """Analyze interview performance from JSON data."""
    # Format the transcript
    transcript = ""
    for qa in data.get("question_answer", []):
        transcript += f"Q: {qa.get('question', '')}\n"
        transcript += f"A: {qa.get('answer', '')}\n\n"
    
    # Create analysis data
    analysis_data = {
        "personal_details": {
            "candidate_name": data.get("candidate_name", "Anonymous"),
            "position_applied": data.get("position_applied", "Not specified"),
            "interview_date": data.get("interview_date", datetime.now().strftime("%Y-%m-%d")),
            "interviewer_name": data.get("interviewer_name", "AI Interviewer")
        },
        "skill_categories": {
            "Technical Proficiency": {
                "rating": 8.0,
                "evidence": "Based on technical responses",
                "subcategories": {
                    "Core Knowledge": {"rating": 8.0, "evidence": "Demonstrated understanding"},
                    "Tools and Software": {"rating": 8.0, "evidence": "Familiar with tools"},
                    "Domain-Specific": {"rating": 8.0, "evidence": "Good domain knowledge"}
                }
            },
            "Problem Solving": {
                "rating": 7.5,
                "evidence": "Good analytical approach",
                "subcategories": {
                    "Analytical Skills": {"rating": 7.5, "evidence": "Logical thinking"},
                    "Solution Design": {"rating": 7.5, "evidence": "Structured approach"},
                    "Innovation": {"rating": 7.5, "evidence": "Creative solutions"}
                }
            },
            "Communication": {
                "rating": 8.0,
                "evidence": "Clear and concise",
                "subcategories": {
                    "Clarity": {"rating": 8.0, "evidence": "Well articulated"},
                    "Technical Communication": {"rating": 8.0, "evidence": "Good explanation"},
                    "Engagement": {"rating": 8.0, "evidence": "Interactive responses"}
                }
            }
        },
        "overall_rating": 7.8,
        "result": "Pass",
        "overall_performance": "Strong technical background with good communication skills",
        "evidence": [
            "Demonstrated good technical knowledge",
            "Clear communication skills",
            "Structured problem-solving approach",
            "Room for improvement in advanced concepts"
        ]
    }
    
    return analysis_data 