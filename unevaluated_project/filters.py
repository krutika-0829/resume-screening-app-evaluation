import json
from llm import analyze_query,match_jd


# extracted_info = store_extracted_info()

# def metadata_filtering(query, extracted_info):
 
#     filters = analyze_query(query)
 
#     try:
#         filters = json.loads(filters)
#     except:
#         filters = {}
#         print("FILTERS : ",filters)
 
#     # normalize all keys to lowercase
#     filters = {k.lower(): v for k, v in filters.items()}
 
#     # lowercase list values
#     if isinstance(filters.get("skills"), list):
#         filters["skills"] = [s.lower() for s in filters["skills"]]
 
#     if isinstance(filters.get("projects"), list):
#         filters["projects"] = [p.lower() for p in filters["projects"]]
 
#     # name always as list
#     if isinstance(filters.get("name"), list):
#         filters["name"] = [n.lower() for n in filters["name"]]
#     elif isinstance(filters.get("name"), str):
#         filters["name"] = [filters["name"].lower()]
 
#     # convert role/education to single string
#     for field in ["role", "education"]:
#         if isinstance(filters.get(field), list):
#             filters[field] = filters[field][0] if filters[field] else None
#         if filters.get(field):
#             filters[field] = filters[field].lower()
 
 
 
#     allowed_sources = set()
 
#     for source, info in extracted_info.items():
#         failed = False
 
#         # name - must match if provided
#         if filters.get("name"):
#             resume_name = (info.get("Name") or "").lower()
#             if not any(fn in resume_name for fn in filters["name"]):
#                 failed = True
 
#         # skills - at least one must match
#         if not failed and filters.get("skills"):
#             resume_skills = [s.lower() for s in (info.get("Skills") or [])]
#             if not any(s in resume_skills for s in filters["skills"]):
#                 failed = True
 
#         # projects - at least one must match
#         if not failed and filters.get("projects"):
#             resume_projects = [p.lower() for p in (info.get("Projects") or [])]
#             if not any(p in resume_projects for p in filters["projects"]):
#                 failed = True
 
#         # role - partial match
#         if not failed and filters.get("role"):
#             resume_role = (info.get("Role") or  "").lower()
#             if filters["role"] not in resume_role:
#                 failed = True
 
#         # education - partial match
#         if not failed and filters.get("education"):
#             resume_education = (info.get("Education")or "").lower()
#             if filters["education"] not in resume_education:
#                 failed = True
 
#         if not failed:
#             allowed_sources.add(source)
 
#     # fallback - if nothing matched return all
#     if not allowed_sources:
#         return set(extracted_info.keys())
 
#     return allowed_sources





def metadata_filtering(query,extracted_info):

    filters = analyze_query(query)
   
    try:
        filters = json.loads(filters)
        
    except:
        filters = {}
        
    for field in ["name", "role", "education"]:
        if isinstance(filters.get(field), list):
            filters[field] = filters[field][0] if filters[field] else None 

    allowed_sources = set()
    
    

    for source, info in extracted_info.items():
        

        if filters.get("skills"):
            resume_skills = [s.lower() for s in info.get("Skills", [])]
            filter_skills = [s.lower() for s in filters["skills"]]
            
                
            if not any(s in resume_skills for s in filter_skills):
                continue


        if filters.get("projects"):
            resume_projects = [p.lower() for p in info.get("Projects", [])]
            filter_projects = [p.lower() for p in filters["projects"]]
           
            if not any(p in resume_projects for p in filter_projects):
               continue


        if filters.get("role"):
            resume_role = (info.get("Role") or "").lower()
            filter_role = filters["role"].lower()
          
                
            if filter_role not in resume_role:
                continue


        if filters.get("education"):
            resume_education = (info.get("Education") or "").lower()
            filter_education = filters["education"].lower()
           
                
            if filter_education not in resume_education:
                continue


        if filters.get("name"):
            resume_name = (info.get("Name") or "").lower()
            filter_name = filters["name"].lower()

            if filter_name not in resume_name:
                   continue

        allowed_sources.add(source)
        

    return allowed_sources





def resume_match_JD(query,extracted_info):

    matches = match_jd(query)
    try:
        matches = json.loads(matches)
        print(matches)
    except:
        matches = {}
    
    for field in ["role", "education"]:
        if isinstance(matches.get(field), list):
            matches[field] = matches[field][0] if matches[field] else None

    resume_scores = {}

    for source, info in extracted_info.items():
        score = 0

        if matches.get("skills"):
            resume_skills = [s.lower() for s in info.get("Skills", [])]
            matches_skills = [s.lower() for s in matches["skills"]]
            
            matching = [s for s in matches_skills if s in resume_skills]
            score += len(matching) * 20
 
        if matches.get("role"):
            resume_role = info.get("Role", "").lower()
            matches_role = matches["role"].lower()
            if matches_role in resume_role:
                score += 15

        if matches.get("education"):
            resume_education = info.get("Education", "").lower()
            matches_education = matches["education"].lower()
            if matches_education in resume_education:
                score += 5



        resume_scores[source] = score
 
    
    sorted_resumes = sorted(resume_scores.items(), key=lambda x: x[1], reverse=True)
 
    results = []
    for source, score in sorted_resumes:
        results.append({
            "name": extracted_info[source].get("Name"),
            "role": extracted_info[source].get("Role"),
            "skills": extracted_info[source].get("Skills"),
            "score": score
        })
 
    return results




