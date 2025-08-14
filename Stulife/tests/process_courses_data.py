#!/usr/bin/env python3
"""
Script to process and combine course data from both semesters
"""

import json
from pathlib import Path
from typing import Dict, List, Any

def load_json_file(file_path: Path) -> Dict[str, Any]:
    """Load JSON file with error handling"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return {}

def normalize_course_data(course: Dict[str, Any], semester: str) -> Dict[str, Any]:
    """Normalize course data to standard format"""
    
    # Handle instructor ID
    instructor_id = course.get("instructor", {}).get("id")
    if instructor_id is None:
        # Generate a placeholder ID if missing
        instructor_name = course.get("instructor", {}).get("name", "Unknown")
        instructor_id = f"T{hash(instructor_name) % 10000:04d}"
    
    # Handle prerequisites
    prerequisites = course.get("prerequisites", [])
    if prerequisites and prerequisites[0] == "None":
        prerequisites = []
    
    # Handle location
    location = course.get("schedule", {}).get("location", {})
    room = location.get("room_number", "")
    if not room:
        room = location.get("room", "Unknown Room")
    
    # Normalize the course structure
    normalized = {
        "course_code": course.get("course_code", ""),
        "course_name": course.get("course_name", ""),
        "credits": course.get("credits", 0),
        "total_class_hours": course.get("total_class_hours", 0),
        "instructor": {
            "name": course.get("instructor", {}).get("name", "Unknown"),
            "id": instructor_id
        },
        "schedule": {
            "weeks": course.get("schedule", {}).get("weeks", {"start": 1, "end": 18}),
            "days": course.get("schedule", {}).get("days", []),
            "time": course.get("schedule", {}).get("time", ""),
            "class_hours_per_week": course.get("schedule", {}).get("class_hours_per_week", 0),
            "location": {
                "building_id": location.get("building_id", ""),
                "building_name": location.get("building_name", ""),
                "room": room
            }
        },
        "description": course.get("description", ""),
        "prerequisites": prerequisites,
        "enrollment_capacity": course.get("enrollment_capacity", 0),
        "popularity": course.get("popularity_index", 0),  # Rename for consistency
        "seats_left": course.get("seats_left", 0),
        "total_seats": course.get("enrollment_capacity", 0),  # Add total_seats field
        "type": course.get("type", "Elective"),
        "semester": semester  # Add semester information
    }
    
    return normalized

def combine_courses():
    """Combine courses from both semesters"""
    info_dir = Path("任务数据/background/info")
    output_dir = Path("任务数据/background")
    
    # Load semester 1 courses
    s1_file = info_dir / "combined_courses.json"
    s1_data = load_json_file(s1_file)
    s1_courses = s1_data.get("all_courses", [])
    print(f"📚 Loaded {len(s1_courses)} courses from semester 1")
    
    # Load semester 2 courses
    s2_file = info_dir / "s2_combined_courses.json"
    s2_data = load_json_file(s2_file)
    s2_courses = s2_data.get("all_courses", [])
    print(f"📚 Loaded {len(s2_courses)} courses from semester 2")
    
    # Combine and normalize courses
    all_courses = []
    
    # Process semester 1 courses
    for course in s1_courses:
        normalized = normalize_course_data(course, "Semester 1")
        all_courses.append(normalized)
    
    # Process semester 2 courses
    for course in s2_courses:
        normalized = normalize_course_data(course, "Semester 2")
        all_courses.append(normalized)
    
    print(f"✅ Combined {len(all_courses)} total courses")
    
    # Create final structure
    courses_data = {
        "courses": all_courses,
        "metadata": {
            "total_courses": len(all_courses),
            "semester_1_courses": len(s1_courses),
            "semester_2_courses": len(s2_courses),
            "last_updated": "2024-01-01",
            "description": "Combined course catalog for both semesters"
        }
    }
    
    # Save combined courses
    output_path = output_dir / "courses.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(courses_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Saved combined courses to {output_path}")
    
    # Generate statistics
    print("\n📊 Course Statistics:")
    
    # Count by type
    type_counts = {}
    semester_counts = {}
    
    for course in all_courses:
        course_type = course.get("type", "Unknown")
        semester = course.get("semester", "Unknown")
        
        type_counts[course_type] = type_counts.get(course_type, 0) + 1
        semester_counts[semester] = semester_counts.get(semester, 0) + 1
    
    print("  Course Types:")
    for course_type, count in type_counts.items():
        print(f"    - {course_type}: {count}")
    
    print("  By Semester:")
    for semester, count in semester_counts.items():
        print(f"    - {semester}: {count}")
    
    # Find courses with highest/lowest popularity
    if all_courses:
        sorted_by_popularity = sorted(all_courses, key=lambda x: x.get("popularity", 0), reverse=True)
        print(f"\n  Most Popular Course: {sorted_by_popularity[0]['course_name']} (Popularity: {sorted_by_popularity[0]['popularity']})")
        print(f"  Least Popular Course: {sorted_by_popularity[-1]['course_name']} (Popularity: {sorted_by_popularity[-1]['popularity']})")
    
    return courses_data

def validate_courses_data(courses_data: Dict[str, Any]):
    """Validate the combined courses data"""
    print("\n🔍 Validating courses data...")
    
    courses = courses_data.get("courses", [])
    issues = []
    
    for i, course in enumerate(courses):
        # Check required fields
        required_fields = ["course_code", "course_name", "credits", "instructor"]
        for field in required_fields:
            if not course.get(field):
                issues.append(f"Course {i}: Missing {field}")
        
        # Check instructor ID
        if not course.get("instructor", {}).get("id"):
            issues.append(f"Course {i}: Missing instructor ID")
        
        # Check schedule
        schedule = course.get("schedule", {})
        if not schedule.get("days") or not schedule.get("time"):
            issues.append(f"Course {i}: Incomplete schedule information")
    
    if issues:
        print(f"⚠️  Found {len(issues)} validation issues:")
        for issue in issues[:10]:  # Show first 10 issues
            print(f"    - {issue}")
        if len(issues) > 10:
            print(f"    ... and {len(issues) - 10} more issues")
    else:
        print("✅ All courses data validated successfully")

def main():
    """Main processing function"""
    print("🚀 Starting course data processing...")
    
    # Combine courses from both semesters
    courses_data = combine_courses()
    
    # Validate the combined data
    validate_courses_data(courses_data)
    
    print("\n🎉 Course data processing completed!")

if __name__ == "__main__":
    main()
