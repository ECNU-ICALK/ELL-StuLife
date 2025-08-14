# CampusLifeBench Background Data

This directory contains all the background data required for the CampusLifeBench evaluation framework. The data has been consolidated and standardized to ensure consistent access and English-only content.

## Directory Structure

```
background/
├── bibliography.json          # Consolidated books and handbooks
├── campus_data.json          # Campus information (clubs, advisors, library)
├── map_v1.5.json            # Campus map and building data
├── courses.json             # Course catalog
├── README.md                # This documentation
├── books/                   # Original book files (legacy)
└── info/                    # Original info files (legacy)
```

## Data Files Description

### 1. bibliography.json

**Purpose**: Consolidated repository of all books including handbooks and textbooks.

**Structure**: 
- Root object with `books` array
- Each book follows chapter-section-article hierarchy
- All content is in English

**Available Books**:

#### Handbooks (3 books):
- **Student Handbook**: University policies, academic expectations, and conduct standards
- **Academic Integrity Guidelines**: Guidelines for academic honesty and research ethics
- **Academic Programs Guide**: Comprehensive guide to academic programs including Computer Science, Software Engineering, Data Science, Communication Engineering, and Microelectronics programs

#### Textbooks (8 books):
- **A Panorama of Computing: From Bits to Artificial Intelligence**: Computer science fundamentals
- **Linear Algebra and Its Applications**: Mathematical foundations and applications
- **Mathematical Analysis**: Advanced mathematical concepts and proofs
- **Military Theory and National Defense**: Military strategy and defense concepts
- **Programming for Everyone**: Programming fundamentals and best practices
- **Innovation and Entrepreneurship**: Business innovation and startup methodologies
- **Mental Health and Wellness**: Psychological health and wellness strategies
- **Advanced Programming Concepts**: Advanced software development techniques

**Usage**: Access through `bibliography.*` tools in the system.

### 2. campus_data.json

**Purpose**: Comprehensive campus information including clubs, advisors, and library data.

**Structure**:
```json
{
  "clubs": [...],           // 101 student clubs
  "advisors": [...],        // 1000 faculty advisors
  "library_seats": {...},   // Library seating arrangements
  "library_books": [...]    // 395 library books
}
```

**Content Details**:

#### Clubs (101 total):
- **Categories**: Academic & Technological, Sports & Fitness, Arts & Culture, Community Service, Professional Development, Special Interest
- **Information**: Club ID, name, category, description, recruitment info
- **Example**: Artificial Intelligence Innovation Society, Robotics Enthusiasts Alliance

#### Advisors (1000 total):
- **Research Areas**: Engineering, Computer Science, Mathematics, Physics, Biology, Chemistry, Medicine, Social Sciences, Humanities
- **Information**: Advisor ID, name, contact, research areas, representative work, preferences
- **Example**: Faculty from various departments with diverse research backgrounds

#### Library Data:
- **Seats**: Detailed seating maps for library buildings with seat types and amenities
- **Books**: Catalog of 395 books with location, availability, and metadata

**Usage**: Access through `data_system.*` tools in the system.

### 3. map_v1.5.json

**Purpose**: Campus map data including buildings, paths, and navigation information.

**Structure**:
- Nodes: Buildings with IDs, names, aliases, types, zones, and internal amenities
- Edges: Pathways between buildings with properties (distance, surface type, etc.)
- Building complexes: Grouped building structures

**Usage**: Access through `map.*` and `geography.*` tools in the system.

### 4. courses.json

**Purpose**: Comprehensive course catalog combining both semesters with scheduling and enrollment information.

**Structure**:
```json
{
  "courses": [...],         // 226 total courses
  "metadata": {
    "total_courses": 226,
    "semester_1_courses": 210,
    "semester_2_courses": 16,
    "description": "Combined course catalog for both semesters"
  }
}
```

**Content Details**:
- **Total Courses**: 226 (210 from Semester 1, 16 from Semester 2)
- **Course Types**: 46 Compulsory, 180 Elective
- **Information**: Course code, name, credits, instructor, schedule, location, enrollment data
- **Semester Tracking**: Each course includes semester information
- **Prerequisites**: Dependency tracking between courses
- **Popularity Index**: Course popularity ratings (29-99 range)

**Usage**: Access through `course_selection.*` and `draft.*` tools in the system.

## Data Standards

### Language
- **All content is in English only**
- Consistent terminology and formatting
- Professional academic language

### Encoding
- **UTF-8 encoding** for all files
- Proper JSON formatting with validation
- Consistent indentation (2 spaces)

### Identifiers
- **Unique IDs** for all entities (books, clubs, advisors, courses, etc.)
- Consistent ID formats (e.g., C001 for clubs, T001 for advisors)
- Cross-references maintained between related data

### Structure
- **Hierarchical organization** for books (chapter-section-article)
- **Normalized data structures** across all files
- **Consistent field naming** conventions

## Integration with CampusLifeBench

### System Integration
The background data is automatically loaded by the CampusEnvironment class:

```python
# Data directory detection
background_dir = data_dir / "background"
if background_dir.exists():
    # Use consolidated background data
else:
    # Fallback to legacy data structure
```

### Tool Access
Data is accessible through various tool systems:

- **Bibliography tools**: `bibliography.list_chapters`, `bibliography.view_article`, etc.
- **Data system tools**: `data_system.list_by_category`, `data_system.query_by_identifier`, etc.
- **Map tools**: `map.find_building_id`, `map.get_building_details`, etc.
- **Course tools**: `course_selection.browse_courses`, `draft.add_course`, etc.

### Backward Compatibility
- Legacy `books/` and `info/` directories are preserved
- System automatically detects and uses new consolidated format
- Fallback mechanisms ensure compatibility with existing configurations

## Maintenance

### Data Updates
- Modify consolidated files (`bibliography.json`, `campus_data.json`) directly
- Maintain consistent structure and English-only content
- Validate JSON format after changes

### Adding New Content
- Follow existing data structures and naming conventions
- Ensure all new content is in English
- Update this README when adding new categories or significant changes

### Quality Assurance
- All data has been validated for JSON compliance
- Content reviewed for English-only requirement
- Cross-references verified between related entities

## Version History

- **v1.0** (2024-01): Initial consolidation of background data
- Migrated from distributed files to consolidated structure
- Standardized all content to English
- Implemented unified data access patterns
