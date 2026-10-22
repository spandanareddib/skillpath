from app.services.skills import extract_skills, load_vocabulary


def names(text):
    return {s.name for s in extract_skills(text)}


def test_vocabulary_loads_without_conflicts():
    assert len(load_vocabulary().skills) > 50


def test_aliases_map_to_one_canonical_skill():
    found = extract_skills("Used sklearn and also Scikit Learn.")
    assert [(s.name, s.mentions) for s in found] == [("scikit-learn", 2)]


def test_java_is_not_javascript():
    assert names("Wrote JavaScript") == {"JavaScript"}
    assert names("Java developer") == {"Java"}


def test_symbols_in_skill_names():
    assert names("Experience with C++ and C#.") == {"C++", "C#"}


def test_r_is_case_sensitive_and_not_matched_in_other_words():
    assert "R" in names("Statistical analysis in R and Python")
    assert "R" not in names("The R&D team is ready for the r key")


def test_no_match_inside_longer_words():
    assert "React" not in names("reactive programming")


def test_line_breaks_inside_a_skill_name():
    assert names("machine\nlearning") == {"Machine Learning"}


def test_mentions_and_evidence():
    found = extract_skills("Python. Python projects. Used python daily.")
    assert found[0].name == "Python" and found[0].mentions == 3
    assert "Python" in found[0].evidence


def test_resume_style_skills_block():
    text = (
        "Languages: Java, Python\n"
        "Core Fundamentals: Data Structures & Algorithms (DSA), Object-Oriented Programming(OOPS)\n"
        "Web Development: React.js, HTML5, CSS3, Tailwind CSS, JavaScript\n"
        "Developer Tools: Git, GitHub, VS Code"
    )
    assert names(text) == {
        "Java", "Python", "Data Structures & Algorithms", "Object-Oriented Programming",
        "React", "HTML", "CSS", "Tailwind CSS", "JavaScript", "Git", "GitHub", "VS Code",
    }


def test_dot_js_suffix_is_not_javascript():
    assert names("Express.js and Next.js") == {"Express.js", "Next.js"}
    assert names("Node.js and React.js") == {"Node.js", "React"}


def test_react_flow_is_not_react():
    assert names("React Flow") == {"React Flow"}


def test_gemini_and_structured_extraction():
    assert names("Google Gemini API with structured data extraction") == {
        "Google Gemini API", "Structured Data Extraction"
    }
