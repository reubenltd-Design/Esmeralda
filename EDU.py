
import json
import os
import sqlite3
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

PROFILES = ["Explorer A", "Explorer B", "Explorer C"]
DB = os.environ.get("STEM_DB", "stembridge.sqlite3")

TOPICS = [
    ("Number Sense", "Understand place value and quantities.",
     "The 7 in 4,782 represents 700.", "Hundreds"),
    ("Addition & Subtraction", "Combine and compare quantities.",
     "403 - 178 = 225.", "Difference"),
    ("Multiplication", "Represent equal groups and arrays.",
     "7 rows of 8 = 7 × 8 = 56.", "Equal groups"),
    ("Division", "Understand sharing and grouping.",
     "72 ÷ 9 = 8 because 9 × 8 = 72.", "Inverse operations"),
    ("Fractions", "Represent and combine equal parts.",
     "1/2 + 1/4 = 2/4 + 1/4 = 3/4.", "Common denominator"),
    ("Decimals", "Work with tenths and hundredths.",
     "0.60 + 0.25 = 0.85.", "Decimal place value"),
    ("Geometry", "Measure shapes and spaces.",
     "A 5 cm × 4 cm rectangle has an area of 20 cm².", "Area"),
    ("Rates", "Compare quantities per unit.",
     "18 miles in 3 hours = 6 miles per hour.", "Unit rate"),
    ("Ratios & Percentages", "Reason proportionally.",
     "25% of 80 = 1/4 of 80 = 20.", "Percent"),
    ("Prealgebra", "Solve for unknown values.",
     "3x + 4 = 19; subtract 4 and divide by 3: x = 5.", "Equation")
]

DIAGNOSTIC = [
    (0, "Value of the 7 in 4,782?", ["7","70","700","7000"], 2),
    (1, "403 - 178 = ?", ["225","235","325","231"], 0),
    (2, "7 × 8 = ?", ["48","54","56","64"], 2),
    (3, "72 ÷ 9 = ?", ["7","8","9","6"], 1),
    (4, "1/2 + 1/4 = ?", ["2/6","3/4","1/4","1/8"], 1),
    (5, "0.6 + 0.25 = ?", ["0.31","0.65","0.85","0.86"], 2),
    (6, "Area of a 5 by 4 rectangle?", ["9","18","20","25"], 2),
    (7, "18 miles in 3 hours: miles per hour?", ["3","6","9","15"], 1),
    (8, "25% of 80 = ?", ["15","20","25","40"], 1),
    (9, "Solve 3x + 4 = 19.", ["3","4","5","7"], 2),
    (0, "Which is greatest?", ["0.7","0.67","0.607","0.076"], 0),
    (1, "900 - 456 = ?", ["444","454","544","434"], 0),
    (2, "Six boxes hold nine pencils each. Total?",
     ["45","54","63","69"], 1),
    (3, "84 ÷ 7 = ?", ["11","12","13","14"], 1),
    (4, "Which fraction equals 3/6?", ["1/3","1/2","2/3","3/4"], 1),
    (5, "2.4 × 10 = ?", ["0.24","2.40","24","240"], 2),
    (6, "Perimeter of a square with 6 cm sides?",
     ["12","24","36","18"], 1),
    (7, "Five notebooks cost $15. Cost per notebook?",
     ["$2","$3","$4","$5"], 1),
    (8, "10% of 150 = ?", ["10","15","25","50"], 1),
    (9, "Solve x/4 = 6.", ["2","10","24","30"], 2)
]

MISSIONS = [
    ("Solar Garden",
     "Four solar panels produce 150 watts each. Total power?",
     ["450 W","600 W","750 W"],1,
     "4 × 150 = 600 watts."),
    ("Rover Expedition",
     "A rover travels 3 meters every 2 seconds. How far in 10 seconds?",
     ["12 m","15 m","30 m"],1,
     "Ten seconds has five intervals. 5 × 3 = 15 meters."),
    ("Water Conservation Lab",
     "A system saves 12 liters every day. How much in 7 days?",
     ["19 L","72 L","84 L"],2,
     "12 × 7 = 84 liters."),
    ("Bridge Design",
     "A deck is 8 meters long and 2 meters wide. Its area?",
     ["10 m²","16 m²","20 m²"],1,
     "8 × 2 = 16 square meters.")
]

WEEKS = [
    "Number sense and addition/subtraction",
    "Multiplication and division",
    "Fractions and decimals",
    "Geometry and measurement",
    "Rates, ratios and percentages",
    "Prealgebra and engineering applications"
]


def db_connection():
    db = sqlite3.connect(DB, timeout=15)
    db.row_factory = sqlite3.Row
    return db


def setup():
    with db_connection() as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS results (
            profile TEXT NOT NULL,
            kind TEXT NOT NULL,
            topic INTEGER NOT NULL,
            form INTEGER NOT NULL,
            score INTEGER NOT NULL,
            detail TEXT NOT NULL,
            completed TEXT NOT NULL,
            PRIMARY KEY (profile, kind, topic, form)
        )""")
        db.execute("""
        CREATE TABLE IF NOT EXISTS teacher_focus (
            profile TEXT PRIMARY KEY,
            topic INTEGER NOT NULL
        )""")


def validate_profile(p):
    if p not in PROFILES:
        raise ValueError("Only fictional Explorer profiles are available")
    return p


def validate_topic(t):
    t = int(t)
    if not 0 <= t < 10:
        raise ValueError("Invalid topic")
    return t


def check_question(topic, index, form):
    """Distinct reproducible practice items per topic/form."""
    topic = validate_topic(topic)
    if index not in range(5) or form not in (0, 1):
        raise ValueError("Invalid check question")

    n = index + 2 + form * 6
    unit = ""

    if topic == 0:
        number = 1000 + n * 100 + 47
        prompt = f"What is the value of the hundreds digit in {number:,}?"
        value = (n % 10) * 100
        tip = "Identify the hundreds digit and multiply it by 100."
    elif topic == 1:
        a, b = 235 + n * 17, 65 + n * 4
        prompt = f"Calculate {a} - {b}."
        value = a - b
        tip = "Subtract by place value, regrouping when needed."
    elif topic == 2:
        prompt = f"How many objects are in {n} equal groups of 8?"
        value = n * 8
        tip = "Multiply the number of groups by eight."
    elif topic == 3:
        prompt = f"Calculate {n * 7} ÷ 7."
        value = n
        tip = "Division undoes multiplication."
    elif topic == 4:
        prompt = f"Add {n}/10 + 2/10. Give the numerator in tenths."
        value = n + 2
        tip = "Keep the denominator ten and add the numerators."
    elif topic == 5:
        prompt = f"Add {n/10:.1f} + 0.3. Give the answer in tenths."
        value = n + 3
        tip = "Combine the tenths."
    elif topic == 6:
        prompt = f"What is the area of a {n} by 4 rectangle?"
        value = n * 4
        unit = " square units"
        tip = "Multiply length by width."
    elif topic == 7:
        prompt = f"{n*6} miles in 3 hours. Find miles per hour."
        value = n * 2
        unit = " mph"
        tip = "Divide distance by time."
    elif topic == 8:
        prompt = f"What is 25% of {n*20}?"
        value = n * 5
        tip = "25% is one quarter."
    else:
        prompt = f"Solve 3x + 4 = {3*n+4}. Find x."
        value = n
        tip = "Subtract four and then divide by three."

    choices = [value, value + 1, value + 3]
    offset = (topic + index + form) % 3
    choices = choices[offset:] + choices[:offset]
    return {
        "prompt": prompt,
        "choices": [str(x) + unit for x in choices],
        "correct": choices.index(value),
        "explanation": tip + f" Correct value: {value}{unit}."
    }


def save(profile, kind, topic, form, score, detail):
    with db_connection() as db:
        db.execute("""
            INSERT INTO results VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(profile,kind,topic,form)
            DO UPDATE SET score=excluded.score,
                          detail=excluded.detail,
                          completed=excluded.completed
        """, (profile, kind, topic, form, score,
              json.dumps(detail), date.today().isoformat()))


def get_state(profile):
    with db_connection() as db:
        results = [dict(row) for row in db.execute(
            "SELECT * FROM results WHERE profile=?", (profile,)
        )]
        chosen = db.execute(
            "SELECT topic FROM teacher_focus WHERE profile=?", (profile,)
        ).fetchone()

    for r in results:
        r["detail"] = json.loads(r["detail"])

    return {
        "results": results,
        "focus": chosen["topic"] if chosen else 2
    }


HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>STEM Bridge | Created by Esmeralda Reuben</title>
<style>
:root{--navy:#142b50;--blue:#2563eb;--teal:#0f766e;
--bg:#f3f6fb;--border:#dbe3ee;--text:#172b48}
*{box-sizing:border-box}
body{font:16px system-ui,Arial,sans-serif;background:var(--bg);
color:var(--text);margin:0;line-height:1.55}
header{background:linear-gradient(115deg,#142b50,#116173);
color:white;padding:25px max(20px,calc((100% - 1100px)/2))}
header h1{font-size:38px;margin:5px 0}
header p{margin:4px 0}
nav{background:white;display:flex;flex-wrap:wrap;gap:7px;
padding:12px max(15px,calc((100% - 1100px)/2));
border-bottom:1px solid var(--border)}
main{max-width:1100px;margin:auto;padding:22px 14px 60px}
button,select{font:inherit}
button{cursor:pointer;border:1px solid #cbd5e1;border-radius:9px;
padding:10px 14px;background:white;color:var(--text)}
button:hover{border-color:var(--blue)}
button:focus-visible,select:focus-visible{outline:3px solid #60a5fa}
button:disabled{cursor:not-allowed;opacity:.45}
nav button{border:0}
.primary{background:var(--blue);border-color:var(--blue);color:white}
.active{background:#dbeafe;color:#1e40af;border-color:#93c5fd}
.card{background:white;border:1px solid var(--border);
border-radius:15px;padding:20px;margin-bottom:15px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(225px,1fr));
gap:14px;margin-bottom:15px}
.grid>.card{margin-bottom:0}
.row{display:flex;align-items:center;gap:9px;flex-wrap:wrap}
.between{justify-content:space-between}
h2{font-size:24px;margin:0 0 10px}
h3{font-size:19px;margin:0 0 10px}
.muted{color:#62738b}
.stat{font-size:32px;font-weight:800;color:#1d4e94}
.pill{font-size:12px;display:inline-block;padding:5px 10px;
background:#e2e8f0;border-radius:50px}
.choice{display:block;width:100%;text-align:left;
padding:14px;margin:8px 0}
.choice.chosen{background:#dbeafe;color:#1e40af;border-color:#2563eb}
.progress{background:#e2e8f0;border-radius:20px;height:10px;
overflow:hidden;margin:14px 0}
.progress span{display:block;height:100%;background:#0d9488}
.example{background:#eff6ff;border-left:4px solid var(--blue);
padding:17px;margin:14px 0;border-radius:5px}
.good{color:#047857;font-weight:700}
.warn{color:#a16207;font-weight:700}
.question{font-weight:700;font-size:22px;margin:20px 0}
select{padding:9px;border-radius:9px;border:1px solid var(--border)}
details{padding:12px 0;border-bottom:1px solid var(--border)}
summary{cursor:pointer;font-weight:650}
footer{text-align:center;color:#64748b;font-size:13px;padding:20px}
.sheetitem{border-bottom:1px solid #ddd;padding:22px 0 55px}
@media(max-width:500px){header h1{font-size:29px}}
@media print{
header,nav,.controls,footer{display:none!important}
body{background:white}main{max-width:none}
.card{border:0}
}
</style>
</head>
<body>
<header>
<div style="font-size:12px;letter-spacing:2px">
FOUNDATIONAL MATHEMATICS + ENGINEERING</div>
<h1>STEM Bridge ↗</h1>
<p>Build confidence. Strengthen foundations. Solve real problems.</p>
<p><strong>Created by Esmeralda Reuben</strong></p>
<div style="font-size:12px;opacity:.8;margin-top:12px">
Educational demonstration · Fictional students only</div>
</header>
<nav aria-label="Main navigation">
<button data-page="home">Overview</button>
<button data-page="diagnostic">Diagnostic</button>
<button data-page="learn">Learning Studio</button>
<button data-page="missions">STEM Missions</button>
<button data-page="teacher">Teacher Desk</button>
</nav>
<main>
<div class="row between controls" style="margin-bottom:16px">
<label>Demo learner:
<select id="profile">
<option>Explorer A</option>
<option>Explorer B</option>
<option>Explorer C</option>
</select></label>
<span class="pill">PROOF OF CONCEPT</span>
</div>
<div id="app" aria-live="polite">Loading...</div>
</main>
<footer>STEM Bridge · Created by Esmeralda Reuben<br>
Provisional instruction and assessment. No real student records.</footer>
<script>
"use strict";
const app=document.getElementById("app");
const esc=s=>String(s).replace(/[&<>"']/g,c=>
({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const btn=(label,act,cls="")=>
`<button class="${cls}" data-act="${act}">${label}</button>`;
const bar=(n,max)=>`<div class="progress"><span style="width:
${100*n/max}%"></span></div>`;
let catalog=null,profile="Explorer A",view="home",state=null;
let topic=2,stage=0,selected=null,diagnosticAnswers=[],
di=0,assessment=null,assessmentAnswers=[],ai=0,
form=0,mission=0,resultDetail=null;
let currentQuestion=null;

async function request(path,data){
 const opts=data===undefined?{}:{
 method:"POST",headers:{"Content-Type":"application/json"},
 body:JSON.stringify({...data,profile})};
 const response=await fetch(path,opts);
 const result=await response.json();
 if(!response.ok)throw Error(result.error||"Request failed");
 return result;
}
async function refresh(){
 state=await request("/api/state?profile="+encodeURIComponent(profile));
}
function result(kind,t,f=0){
 return state.results.find(r=>r.kind===kind&&r.topic===t&&r.form===f);
}
function options(arr,mode){
 return arr.map((x,i)=>
 `<button data-act="${mode}:${i}" class="choice
 ${selected===i?"chosen":""}">
 <strong>${String.fromCharCode(65+i)}.</strong> ${esc(x)}</button>`).join("");
}
function selectTopic(){
 return `<select id="topics" aria-label="Topic">`+
 catalog.topics.map((x,i)=>
 `<option value="${i}" ${i===topic?"selected":""}>${esc(x.name)}</option>`
 ).join("")+"</select>";
}
function set(html){app.innerHTML=html}
function card(title,body){return `<div class="card"><h2>${title}</h2>${body}</div>`}
async function go(target){
 view=target;await refresh();
 document.querySelectorAll("[data-page]").forEach(x=>
 x.classList.toggle("active",x.dataset.page===target));
 if(target==="home")home();
 if(target==="diagnostic")diagnostic();
 if(target==="learn")await learn();
 if(target==="missions")missions();
 if(target==="teacher")teacher();
}
function home(){
 const d=result("diagnostic",-1);
 const m=state.results.filter(x=>x.kind==="mission").length;
 set(card("Welcome to your learning bridge",
 `<p>Develop mathematical understanding through clear models,
 guided practice and real-world engineering.</p>`)+`
 <div class="grid">
 <div class="card"><div class="muted">Diagnostic</div>
 <div class="stat">${d?d.score+"/20":"Not started"}</div>
 ${btn("Open diagnostic","goto:diagnostic","primary")}</div>
 <div class="card"><div class="muted">Mathematics topics</div>
 <div class="stat">10</div>
 ${btn("Explore lessons","goto:learn","primary")}</div>
 <div class="card"><div class="muted">Engineering missions attempted</div>
 <div class="stat">${m}/4</div>
 ${btn("Open lab","goto:missions","primary")}</div></div>`+
 card("Teacher-selected learning focus",
 `<h3>${esc(catalog.topics[state.focus].name)}</h3>
 <p>${esc(catalog.topics[state.focus].description)}</p>
 ${btn("Begin lesson","focus:"+state.focus,"primary")}`)+
 card("Our learning method",
 `<div class="grid">
 <div><b>1. Model</b><p>Make the mathematics visible.</p></div>
 <div><b>2. Explain</b><p>Use precise mathematical language.</p></div>
 <div><b>3. Practice</b><p>Apply and explain a strategy.</p></div>
 <div><b>4. Revisit</b><p>Check learning across days.</p></div>
 </div>`));
}
async function diagnostic(){
 if(resultDetail&&resultDetail.kind==="diagnostic"){
   const r=resultDetail.data;
   set(card("Diagnostic snapshot",
    `<div class="stat">${r.score}/20</div>
     <p class="muted">This is an instructional starting point,
     not a validated test or grade-level estimate.</p>`+
     catalog.topics.map((x,i)=>
     `<div class="row between"><b>${esc(x.name)}</b>
     <span>${r.by_topic[i]}/2</span></div>
     ${bar(r.by_topic[i],2)}
     ${btn("Practice","focus:"+i)}`).join("")+
     `<p>${btn("Retake","restartDiagnostic")}</p>`));
   return;
 }
 if(!assessment||assessment.kind!=="diagnostic")
   assessment={kind:"diagnostic",
    questions:(await request("/api/diagnostic")).questions};
 const q=assessment.questions[di];
 selected=diagnosticAnswers[di]??null;
 set(card("Foundation Diagnostic",
 `<div class="row between"><span class="pill">
 Question ${di+1} of 20</span>
 <span class="muted">${esc(catalog.topics[q.topic].name)}</span></div>
 ${bar(di+1,20)}
 <div class="question">${esc(q.prompt)}</div>
 ${options(q.choices,"diaganswer")}
 <div class="row controls">
 ${btn("Previous","diagback")}
 ${btn(di===19?"Submit diagnostic":"Next →","diagnext","primary")}
 </div><p class="muted">No time limit. Two questions per topic.</p>`));
}
async function diagnosticNext(){
 if(diagnosticAnswers[di]===undefined)
  return alert("Choose an answer before continuing.");
 if(di<19){di++;return diagnostic();}
 const r=await request("/api/diagnostic",
 {answers:diagnosticAnswers});
 resultDetail={kind:"diagnostic",data:r};
 await refresh();diagnostic();
}
function visual(){
 if(topic===2){
 let rects="";
 for(let r=0;r<7;r++)for(let c=0;c<8;c++)
 rects+=`<rect x="${c*23+2}" y="${r*23+2}" width="18"
 height="18" rx="3" fill="#0d9488"/>`;
 return `<svg width="200" height="175" viewBox="0 0 200 175"
 role="img" aria-label="Seven rows of eight squares representing 56">
 ${rects}</svg><p>Seven rows of eight squares = 56.</p>`;
 }
 if(topic===4){
 return `<svg width="320" height="65" viewBox="0 0 320 65"
 role="img" aria-label="Three out of four equal parts shaded">
 ${[0,1,2,3].map(i=>`<rect x="${i*78+2}" y="5" width="74"
 height="45" stroke="#2563eb"
 fill="${i<3?"#93c5fd":"white"}"/>`).join("")}</svg>
 <p>Two fourths plus one fourth is three fourths.</p>`;
 }
 return `<div class="example">${esc(catalog.topics[topic].example)}</div>`;
}
async function learn(){
 const t=catalog.topics[topic];
 let html=`<div class="card"><div class="row between">
 <div><h2>Learning Studio</h2><p class="muted">${esc(t.description)}</p>
 </div>${selectTopic()}</div>
 <div class="row controls">
 ${btn("1. Model","stage:0",stage===0?"active":"")}
 ${btn("2. Guided practice","stage:1",stage===1?"active":"")}
 ${btn("3. Check","stage:2",stage===2?"active":"")}
 </div></div>`;
 if(stage===0){
 html+=card("Understand the concept",
 `<p><strong>Key vocabulary:</strong> ${esc(t.vocabulary)}</p>
 <p>${esc(t.description)}</p>${visual()}
 <h3>Worked example</h3>
 <div class="example">${esc(t.example)}</div>
 <p>Explain what the quantities represent and why the operation is appropriate.</p>
 ${btn("Try guided practice →","stage:1","primary")}`);
 }else if(stage===1){
 const r=await request(`/api/questions?topic=${topic}&form=0`);
 currentQuestion=r.questions[0];selected=null;
 html+=card("Guided practice",
 `<p>Choose an answer, then examine the explanation.</p>
 <div class="question">${esc(currentQuestion.prompt)}</div>
 ${options(currentQuestion.choices,"pick")}
 ${btn("Check and explain","gradeGuided","primary")}
 <div id="feedback" role="status"></div>
 <p>${btn("Show model","stage:0")}
 ${btn("Independent check →","stage:2")}</p>`);
 }else{
 const a=result("check",topic,0),b=result("check",topic,1);
 html+=card("Independent mathematics checks",
 `<p>Complete five questions in Form A. Form B can be attempted
 on a later calendar day to revisit learning.</p>
 <div class="grid">
 <div><h3>Form A</h3><p>${a?a.score+"/5":"Not attempted"}</p>
 ${btn("Open Form A","begin:0","primary")}</div>
 <div><h3>Form B</h3><p>${b?b.score+"/5":"Later-day review"}</p>
 ${btn("Open Form B","begin:1")}</div></div>
 <p class="muted">Scores are provisional practice evidence.
 A teacher should also examine reasoning and transfer.</p>`);
 }
 set(html);
 document.getElementById("topics").onchange=e=>{
 topic=Number(e.target.value);stage=0;learn();
 };
}
async function beginCheck(f){
 const a=result("check",topic,0);
 if(f===1&&(!a||a.completed>=localDay())){
  alert("Form B requires Form A from an earlier day.");
  return;
 }
 form=f;ai=0;assessmentAnswers=[];
 assessment={kind:"check",questions:
 (await request(`/api/questions?topic=${topic}&form=${form}`)).questions};
 checkScreen();
}
function localDay(){
 const d=new Date();
 return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
}
function checkScreen(){
 const q=assessment.questions[ai];
 selected=assessmentAnswers[ai]??null;
 set(card(`Independent Check · Form ${form?"B":"A"}`,
 `<span class="pill">Question ${ai+1}/5</span>
 ${bar(ai+1,5)}
 <div class="question">${esc(q.prompt)}</div>
 ${options(q.choices,"checkanswer")}
 ${btn(ai===4?"Grade my work":"Next →","checknext","primary")}`));
}
async function checkNext(){
 if(assessmentAnswers[ai]===undefined)
  return alert("Choose an answer first.");
 if(ai<4){ai++;return checkScreen();}
 const r=await request("/api/check",
 {topic,form,answers:assessmentAnswers});
 await refresh();
 set(card("Practice check results",
 `<div class="stat">${r.score}/5</div>
 <p>${r.score===5?"All five correct.":"Review your strategies below."}</p>
 ${r.feedback.map((x,i)=>`<details ${x.correct?"":"open"}>
 <summary>${i+1}. ${esc(x.prompt)}
 — ${x.correct?"Correct":"Review"}</summary>
 <p>Correct answer: ${esc(x.expected)}</p>
 <p>${esc(x.explanation)}</p>
 </details>`).join("")}
 <p>${btn("Return to Learning Studio","goto:learn","primary")}</p>`));
}
function missions(){
 const m=catalog.missions[mission];selected=null;
 set(card("Engineering Design Lab",
 `<p>Apply mathematics to meaningful engineering challenges.</p>`)+
 `<div class="grid">${catalog.missions.map((x,i)=>
 `<div class="card"><h3>${esc(x.name)}</h3>
 ${btn("Explore","mission:"+i,mission===i?"active":"")}</div>`
 ).join("")}</div>`+
 card(m.name,
 `<p>${esc(m.context)}</p>
 <div class="question">${esc(m.question)}</div>
 ${options(m.choices,"pick")}
 ${btn("Evaluate calculation","gradeMission","primary")}
 <div id="feedback" role="status"></div>
 <p class="muted">Engineering reflection: Which measurements
 or assumptions would be needed in a real design?</p>`));
}
function teacher(){
 topic=state.focus;
 const d=result("diagnostic",-1);
 set(card("Teacher Desk",
 `<p>Explore learner progress, choose instruction, and prepare
 classroom activities. All profiles are fictional.</p>`)+
 `<div class="grid">
 <div class="card"><h3>Active demonstration learner</h3>
 <div class="stat">${esc(profile)}</div>
 <p>Diagnostic: ${d?d.score+"/20":"Not completed"}</p>
 <p>Check forms recorded:
 ${state.results.filter(x=>x.kind==="check").length}</p></div>
 <div class="card"><h3>Instructional recommendation</h3>
 ${selectTopic()}<p>Teacher choice overrides automated suggestions.</p>
 ${btn("Save focus","saveFocus","primary")}
 <p id="saved" role="status"></p></div></div>`+
 card("Topic check progress",
 catalog.topics.map((t,i)=>{
 const a=result("check",i,0),b=result("check",i,1);
 return `<div class="row between" style="border-bottom:1px solid #ddd;
 padding:10px 0"><b>${esc(t.name)}</b><span>
 A: ${a?a.score+"/5":"—"} · B: ${b?b.score+"/5":"—"}
 </span></div>`;
 }).join(""))+
 card("Six-week / 18-session teaching sequence",
 catalog.weeks.map((w,i)=>
 `<details><summary>Week ${i+1}: ${esc(w)}</summary>
 <ol><li>Session ${i*3+1}: model and discuss</li>
 <li>Session ${i*3+2}: guided practice and feedback</li>
 <li>Session ${i*3+3}: independent check and application</li></ol>
 <p>Include brief spaced retrieval from previous sessions.</p>
 </details>`).join(""))+
 card("Printable practice worksheet",
 `<p>Use the selected topic to create a five-question worksheet.</p>
 ${btn("Generate worksheet","worksheet","primary")}`)+
 card("Teacher review",
 `<p>Diagnostic scores are not grade-level labels. One missed
 item does not establish a skill deficit. Confirm patterns through
 classroom observation, discussion and additional assessment.</p>`));
 document.getElementById("topics").onchange=e=>
 topic=Number(e.target.value);
}
async function worksheet(){
 const qs=(await request(`/api/questions?topic=${topic}&form=0`)).questions;
 set(`<div class="controls row" style="margin-bottom:15px">
 ${btn("Print worksheet","print","primary")}
 ${btn("Back to Teacher Desk","goto:teacher")}</div>`+
 card("STEM Bridge",
 `<p><b>Created by Esmeralda Reuben</b></p>
 <h3>${esc(catalog.topics[topic].name)} — Practice Worksheet</h3>
 <p>Name: ________________________ Date: ______________</p>
 <p>Show your calculation and explain your reasoning.</p>
 ${qs.map((q,i)=>
 `<div class="sheetitem"><b>${i+1}.</b> ${esc(q.prompt)}</div>`
 ).join("")}
 <p>Reflection: What strategy was most useful, and why?</p>
 <p>___________________________________________________</p>`));
}
document.querySelector("nav").addEventListener("click",e=>{
 const b=e.target.closest("[data-page]");
 if(b)go(b.dataset.page).catch(error);
});
document.getElementById("profile").onchange=e=>{
 profile=e.target.value;assessment=null;resultDetail=null;
 diagnosticAnswers=[];di=0;go("home").catch(error);
};
document.addEventListener("click",async e=>{
 const b=e.target.closest("[data-act]");if(!b)return;
 const [act,arg]=b.dataset.act.split(":");
 try{
 if(act==="goto"){await go(arg);return}
 if(act==="focus"){topic=Number(arg);stage=0;await go("learn");return}
 if(act==="diaganswer"){
 diagnosticAnswers[di]=Number(arg);await diagnostic();return}
 if(act==="diagback"){di=Math.max(0,di-1);await diagnostic();return}
 if(act==="diagnext"){await diagnosticNext();return}
 if(act==="restartDiagnostic"){
 assessment=null;resultDetail=null;di=0;diagnosticAnswers=[];
 await diagnostic();return}
 if(act==="stage"){stage=Number(arg);await learn();return}
 if(act==="pick"){
 selected=Number(arg);
 document.querySelectorAll(".choice").forEach((x,i)=>
 x.classList.toggle("chosen",i===selected));return}
 if(act==="gradeGuided"){
 if(selected===null)return alert("Select an answer.");
 const r=await request("/api/guided",{topic,answer:selected});
 document.getElementById("feedback").innerHTML=
 `<p class="${r.correct?"good":"warn"}">
 ${r.correct?"Correct!":"Review the reasoning."}</p>
 <p>Expected answer: ${esc(r.expected)}</p>
 <p>${esc(r.explanation)}</p>`;return}
 if(act==="begin"){await beginCheck(Number(arg));return}
 if(act==="checkanswer"){
 assessmentAnswers[ai]=Number(arg);checkScreen();return}
 if(act==="checknext"){await checkNext();return}
 if(act==="mission"){mission=Number(arg);missions();return}
 if(act==="gradeMission"){
 if(selected===null)return alert("Choose an answer.");
 const r=await request("/api/mission",
 {mission,answer:selected});
 document.getElementById("feedback").innerHTML=
 `<p class="${r.correct?"good":"warn"}">
 ${r.correct?"Correct!":"Review the calculation."}</p>
 <p>${esc(r.explanation)}</p>`;return}
 if(act==="saveFocus"){
 await request("/api/focus",{topic});
 await refresh();
 document.getElementById("saved").textContent="Focus saved.";
 return}
 if(act==="worksheet"){await worksheet();return}
 if(act==="print"){window.print();return}
 }catch(err){error(err)}
});
function error(err){
 console.error(err);
 alert("STEM Bridge: "+err.message);
}
(async function(){
 try{
 catalog=await request("/api/catalog");
 await go("home");
 }catch(err){
 app.innerHTML=card("Cannot reach the Python server",
 `<p>${esc(err.message)}</p>
 <p>Start app.py and open the website through its server address.</p>`);
 }
})();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def respond(self, obj, status=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_body(self):
        size = int(self.headers.get("Content-Length", "0"))
        if not 0 < size <= 12000:
            raise ValueError("Request body length invalid")
        obj = json.loads(self.rfile.read(size))
        if not isinstance(obj, dict):
            raise ValueError("JSON object required")
        return obj

    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            path = parsed.path

            if path == "/":
                body = HTML.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type",
                                 "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if path == "/api/catalog":
                return self.respond({
                    "profiles": PROFILES,
                    "topics": [
                        {"name": t[0], "description": t[1],
                         "example": t[2], "vocabulary": t[3]}
                        for t in TOPICS
                    ],
                    "weeks": WEEKS,
                    "missions": [
                        {"name": m[0], "context": m[0],
                         "question": m[1], "choices": m[2]}
                        for m in MISSIONS
                    ]
                })

            if path == "/api/diagnostic":
                return self.respond({
                    "questions": [
                        {"topic": q[0], "prompt": q[1],
                         "choices": q[2]}
                        for q in DIAGNOSTIC
                    ]
                })

            if path == "/api/state":
                p = parse_qs(parsed.query).get("profile", [""])[0]
                return self.respond(get_state(validate_profile(p)))

            if path == "/api/questions":
                query = parse_qs(parsed.query)
                t = validate_topic(query.get("topic", [""])[0])
                f = int(query.get("form", ["0"])[0])
                questions = []
                for i in range(5):
                    q = check_question(t, i, f)
                    questions.append({
                        "prompt": q["prompt"],
                        "choices": q["choices"]
                    })
                return self.respond({"questions": questions})

            return self.respond({"error": "Route not found"}, 404)

        except (ValueError, TypeError, KeyError) as exc:
            return self.respond({"error": str(exc)}, 400)

    def do_POST(self):
        try:
            path = urlparse(self.path).path
            data = self.read_body()
            p = validate_profile(data.get("profile"))

            if path == "/api/diagnostic":
                answers = data.get("answers")
                if not isinstance(answers, list) or len(answers) != 20:
                    raise ValueError("All 20 answers are required")
                if any(type(a) is not int or a not in range(4)
                       for a in answers):
                    raise ValueError("Invalid diagnostic answers")

                scores = [0] * 10
                for i, a in enumerate(answers):
                    if a == DIAGNOSTIC[i][3]:
                        scores[DIAGNOSTIC[i][0]] += 1

                save(p, "diagnostic", -1, 0, sum(scores), scores)
                return self.respond({
                    "score": sum(scores), "by_topic": scores
                })

            if path == "/api/guided":
                t = validate_topic(data.get("topic"))
                a = data.get("answer")
                if type(a) is not int or a not in range(3):
                    raise ValueError("Invalid answer")
                q = check_question(t, 0, 0)
                return self.respond({
                    "correct": a == q["correct"],
                    "expected": q["choices"][q["correct"]],
                    "explanation": q["explanation"]
                })

            if path == "/api/check":
                t = validate_topic(data.get("topic"))
                f = data.get("form")
                answers = data.get("answers")
                if type(f) is not int or f not in (0, 1):
                    raise ValueError("Invalid form")
                if (not isinstance(answers, list) or len(answers) != 5
                    or any(type(a) is not int or a not in range(3)
                           for a in answers)):
                    raise ValueError("Five valid answers required")

                if f == 1:
                    previous = next(
                        (r for r in get_state(p)["results"]
                         if r["kind"] == "check"
                         and r["topic"] == t and r["form"] == 0), None
                    )
                    if not previous or previous["completed"] >= date.today().isoformat():
                        raise ValueError(
                            "Form B requires Form A from an earlier day"
                        )

                qs = [check_question(t, i, f) for i in range(5)]
                score = sum(
                    answers[i] == q["correct"]
                    for i, q in enumerate(qs)
                )
                feedback = [
                    {
                        "prompt": q["prompt"],
                        "correct": answers[i] == q["correct"],
                        "expected": q["choices"][q["correct"]],
                        "explanation": q["explanation"]
                    }
                    for i, q in enumerate(qs)
                ]
                save(p, "check", t, f, score, feedback)
                return self.respond({
                    "score": score, "feedback": feedback
                })

            if path == "/api/mission":
                mid = data.get("mission")
                a = data.get("answer")
                if type(mid) is not int or mid not in range(4):
                    raise ValueError("Invalid mission")
                if type(a) is not int or a not in range(3):
                    raise ValueError("Invalid answer")
                m = MISSIONS[mid]
                correct = a == m[3]
                save(p, "mission", mid, 0, int(correct), {})
                return self.respond({
                    "correct": correct, "explanation": m[4]
                })

            if path == "/api/focus":
                t = validate_topic(data.get("topic"))
                with db_connection() as db:
                    db.execute("""
                    INSERT INTO teacher_focus VALUES (?,?)
                    ON CONFLICT(profile) DO UPDATE SET topic=excluded.topic
                    """, (p, t))
                return self.respond({"saved": True})

            return self.respond({"error": "Route not found"}, 404)

        except (ValueError, TypeError, KeyError,
                json.JSONDecodeError) as exc:
            return self.respond({"error": str(exc)}, 400)


if __name__ == "__main__":
    setup()
    port = int(os.environ.get("PORT", "8000"))
    print(f"STEM Bridge → http://localhost:{port}", flush=True)
    print("Fictional demo users only.", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()