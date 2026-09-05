import os
import re

html_to_tsx_map = {
    "FINCTRL-AI_Login_Page.html": "Login.tsx",
    "FINCTRL-AI_Dashboard_(Light_Corporate).html": "Dashboard.tsx",
    "FINCTRL-AI_Reconciliation_Workspace.html": "Reconciliation.tsx",
    "FINCTRL-AI_Case_Investigation_(CASE-00001).html": "CaseInvestigation.tsx",
    "FINCTRL-AI_Exceptions_Workspace.html": "Exceptions.tsx",
    "FINCTRL-AI_Human_Review_Workspace.html": "HumanReview.tsx",
    "FINCTRL-AI_Finance_Q&A.html": "FinanceQA.tsx",
    "FINCTRL-AI_Cash_Forecast.html": "CashForecast.tsx",
    "FINCTRL-AI_Tax_Matching_Workspace.html": "TaxMatching.tsx",
    "FINCTRL-AI_Audit_Trail_Workspace.html": "AuditTrail.tsx",
}

def html_to_jsx(html):
    jsx = html
    # Basic class conversions
    jsx = jsx.replace('class=', 'className=')
    jsx = jsx.replace('for=', 'htmlFor=')
    jsx = jsx.replace('<!--', '{/*')
    jsx = jsx.replace('-->', '*/}')
    
    # SVG attributes
    jsx = jsx.replace('stroke-width', 'strokeWidth')
    jsx = jsx.replace('stroke-linecap', 'strokeLinecap')
    jsx = jsx.replace('stroke-linejoin', 'strokeLinejoin')
    jsx = jsx.replace('fill-rule', 'fillRule')
    jsx = jsx.replace('clip-rule', 'clipRule')
    jsx = jsx.replace('viewbox', 'viewBox')
    jsx = jsx.replace('preserveaspectratio', 'preserveAspectRatio')

    # Boolean attributes
    jsx = jsx.replace('disabled=""', 'disabled')
    jsx = jsx.replace('disabled="disabled"', 'disabled')
    jsx = jsx.replace('checked=""', 'checked')
    jsx = jsx.replace('checked="checked"', 'checked')
    jsx = jsx.replace('selected=""', 'selected')
    jsx = jsx.replace('selected="selected"', 'selected')
    jsx = jsx.replace('required=""', 'required')
    jsx = jsx.replace('required="required"', 'required')

    # Event handlers - just strip them
    jsx = re.sub(r'onclick=(["\'])(.*?)\1', '', jsx, flags=re.IGNORECASE)
    jsx = re.sub(r'onsubmit=(["\'])(.*?)\1', '', jsx, flags=re.IGNORECASE)
    
    # tabIndex="0" to tabIndex={0}
    jsx = re.sub(r'tabindex=(["\'])(.*?)\1', r'tabIndex={\2}', jsx, flags=re.IGNORECASE)
    
    # webgl-shader custom element
    jsx = re.sub(r'<webgl-shader[^>]*>', '<div>', jsx)
    jsx = jsx.replace('</webgl-shader>', '</div>')

    # Self-closing tags
    tags = ['img', 'input', 'br', 'hr', 'link', 'meta']
    for tag in tags:
        pattern = re.compile(r'(<' + tag + r'\b[^>]*)(?<!/)>', re.IGNORECASE)
        jsx = pattern.sub(r'\1 />', jsx)
        
    # Styles e.g., style="width: 50%" to style={{ width: '50%' }}
    def style_repl(match):
        style_str = match.group(2)
        parts = style_str.split(';')
        react_styles = []
        for p in parts:
            if ':' in p:
                k, v = p.split(':', 1)
                k = k.strip()
                v = v.strip().replace('"', "'")
                # camelCase the key
                k_parts = k.split('-')
                k_camel = k_parts[0] + ''.join(x.title() for x in k_parts[1:])
                react_styles.append(f"{k_camel}: `{v}`")
        return "style={{" + ", ".join(react_styles) + "}}"

    jsx = re.sub(r'style=(["\'])(.*?)\1', style_repl, jsx)

    # Some SVG/HTML attributes might need fixing:
    # "required" with boolean strings like `required="true"`
    jsx = re.sub(r'required=(["\'])(true|false)\1', r'required={\2}', jsx)

    return jsx

def extract_main_content(html):
    main_match = re.search(r'<main[^>]*>(.*?)</main>', html, re.DOTALL | re.IGNORECASE)
    if main_match:
        return f"<div className=\"w-full h-full flex flex-col\">\n{html_to_jsx(main_match.group(1))}\n</div>"
    
    body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
    if body_match:
        return f"<div className=\"w-full h-full flex flex-col\">\n{html_to_jsx(body_match.group(1))}\n</div>"
        
    return f"<div>\n{html_to_jsx(html)}\n</div>"

for html_file, tsx_file in html_to_tsx_map.items():
    html_path = os.path.join("stitch_screens", html_file)
    tsx_path = os.path.join("src", "pages", tsx_file)
    
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
            
        jsx_content = extract_main_content(html_content)
        
        component_name = tsx_file.replace(".tsx", "")
        # Omit importing React if unused to fix TS error, or just use TS comment
        full_content = f"""// @ts-nocheck
import React from 'react';

export default function {component_name}() {{
  return (
    {jsx_content}
  );
}}
"""
        with open(tsx_path, "w", encoding="utf-8") as f:
            f.write(full_content)
        print(f"Converted {html_file} to {tsx_file}")
