#!/usr/bin/env python3
"""proposal_lint.py - mechanical checks for an Upwork proposal.

It answers three questions a person cannot answer reliably by eye:
  PREVIEW  What does the client see before clicking, and does it earn the click?
  FIT      Does the text use this job's own details, show proof, and end with a next step?
  VOICE    Which machine-writing patterns and stock phrases are in it?

It is NOT an AI detector and NOT a quality verdict. A clean result means the
mechanical problems are gone; the judgment checklists in references/ still apply.

Usage
  python proposal_lint.py --proposal letter.txt
  python proposal_lint.py --proposal letter.txt --job job.txt
  python proposal_lint.py --proposal letter.txt --job job.txt --answers answers.txt
  python proposal_lint.py --proposal letter.txt --history past_letters/ --json
  python proposal_lint.py --proposal-text "Hi, I am a developer..." --job-text "We need..."

  --answers   screening answers, one per block, blocks separated by a line of ---
  --history   a folder of .txt letters, or a JSON list of strings / {"cover_letter": "..."}
  --json      machine-readable output

Python 3.8+, standard library only.
"""
import argparse
import json
import os
import re
import statistics
import sys

PREVIEW_CHARS = 200          # reported previews range from ~150 to ~225 characters; Upwork publishes no number
PREVIEW_SAFE = 150

STOP = set("""
a about above after again against all also am an and any are aren't as at be because been before being below
between both but by can can't cannot could couldn't did didn't do does doesn't doing don't down during each few for
from further had hadn't has hasn't have haven't having he he'd he'll he's her here here's hers herself him himself
his how how's i i'd i'll i'm i've if in into is isn't it it's its itself let's me more most mustn't my myself no nor
not of off on once only or other ought our ours ourselves out over own same shan't she she'd she'll she's should
shouldn't so some such than that that's the their theirs them themselves then there there's these they they'd
they'll they're they've this those through to too under until up very was wasn't we we'd we'll we're we've were
weren't what what's when when's where where's which while who who's whom why why's will with won't would wouldn't
you you'd you'll you're you've your yours yourself yourselves just get got will shall may might must etc via per
without within anything something everything nothing anyone everyone us even still already yet now today around
really much many lot lots every another either neither whether since however therefore thus though although unless
sure hello hi hey look see going come take give put keep say said tell ask show try back way bit kind sort some can
""".split())

# Everyday proposal vocabulary. A sentence built only from these says nothing a rival could not say.
COMMON = set("""
takes took gives gave send sends sent begin begins finish complete completed completing ensure ensures deliver
delivers delivering provide offering offer offers discuss talk chat call message contact reach happy glad love
confident ready immediately right away quickly fast efficiently professionally expertise skilled result results
perfect fit match approach process plan step steps goals goal vision idea ideas satisfaction deadline deadlines
timeline budget updates update regular daily clear maintainable scalable responsive design designs user-friendly
friendly several done do did hear hearing soon hope wish feel free kindly question questions further information
info check review attached profile everything way always never first then next once working results-driven
committed commitment dedicated passionate reliable trusted trust value valuable successful successfully success
smooth smoothly effective effectively efficient top notch amazing awesome exceptional outstanding excellent
understand believe think know guarantee promise assure expect meet exceed expectations requirement needs wants
start started starting work worked working works collaborate collaboration partner partnership relationship
""".split())

NUMBER_WORDS = set("one two three four five six seven eight nine ten eleven twelve fourteen fifteen twenty thirty forty fifty hundred thousand half".split())

# Words that appear in almost every job post; they prove nothing when repeated back.
GENERIC_JOB = set("""
looking need needs needed want wants wanted require required requires requirement requirements developer developers
development develop engineer engineers designer designers freelancer freelancers expert experts experienced experience
experiences project projects work works working worked job jobs role team teams company business client clients please
strong skill skills ability able good great excellent best quality high someone anyone person candidate candidates
help helps build builds building built create creates creating created make makes making made new existing current
currently time times long term short ongoing start starting started asap soon week weeks month months day days hour
hours hourly fixed price budget rate rates pay paid payment apply applying application proposal proposals include
including includes included provide provides provided send share sharing shared know knowledge understanding understand
familiar familiarity proven track record communication english fluent available availability deliver delivery
delivered deliverables task tasks thing things use using used like well also must should nice plus bonus ideal ideally
similar previous past portfolio samples sample examples example relevant detail details detailed description brief
overview summary responsibilities qualifications preferred within based full part hire hiring hired position
opportunity support looking forward thanks thank regards website websites site sites app apps application applications
platform product products feature features user users page pages system systems solution solutions service services
tool tools code simple clean modern professional fully ensure ensuring various multiple different specific
specifically across etc year years level senior junior mid lead one two three first second need needs
posted ago minutes verified spent intermediate entry interviewing invites connects upwork
""".split())

ACRONYM_OK = set("""API APIS UI UX SEO CSS HTML SQL AWS GCP CMS CRM ERP SAAS MVP JSON REST CRUD SDK CLI CI CD QA PR
RLS SSR SSG ISR CDN DNS URL HTTP HTTPS JWT OAUTH GDPR HIPAA KPI ROI B2B B2C PDF CSV PWA IOS RTL LTR GLTF GLB HDRI
FPS GPU CPU RAM SVG PNG JPG GSAP R3F NDA USD EUR GBP UTC GMT EST PST CET IST PKT AI ML LLM RAG ETL ASAP FAQ TBD NFT
SOAP XML YAML PHP WP""".split())


# ----------------------------------------------------------------------------------------------- pattern tables
def rx(p):
    return re.compile(p, re.IGNORECASE | re.MULTILINE)


BLOCKERS = [
    ("AI-tool tracking tag in a link",
     rx(r"[?&](?:utm_[a-z]+|ref|referrer|source)=[^\s&]*(?:chatgpt|openai|claude|anthropic|copilot|gemini|grok|perplexity|llm)[^\s&]*"),
     "A link carries a tag such as utm_source=chatgpt or =claude. It tells the client an AI tool produced the link. Cut everything from the ? onward."),
    ("Unfilled placeholder",
     rx(r"\[(?:your|client|company|project|insert|name|first name|x|link|number|date|portfolio|job|skill)[^\]\n]{0,40}\]|\{\{?\s*[a-z_ ]{2,30}\s*\}?\}|<(?:your|client|insert|name|link)[^>\n]{0,40}>|\blorem ipsum\b|\bINSERT[_ ][A-Z_]+\b|\bTODO\b"),
     "Template placeholder left in the text."),
    ("Chatbot leftover",
     rx(r"^(?:sure|certainly|of course|absolutely)[!,.]\s|\bhere(?:'s| is) (?:a|an|your|the) (?:revised|updated|polished|improved|refined|tailored|draft|proposal|cover letter|version|rewrite)\b|\bi hope this helps\b|\blet me know if you(?:'d| would) like (?:me to|any|a|further)\b|\bas an ai\b|\bfeel free to (?:customi[sz]e|adjust|modify|tweak|edit)\b|^\s*(?:word count|subject)\s*:"),
     "Text that was addressed to you by a chatbot, not to the client."),
    ("Markdown that Upwork prints literally",
     rx(r"\*\*[^*\n]+\*\*|^#{1,6}\s+\S|\[[^\]\n]+\]\(https?://[^)\s]+\)|```"),
     "Upwork cover letters are plain text. Asterisks, # headings and [text](link) show up as raw symbols."),
]

STOCK = [  # (label, regex, points, advice)
    ("wellness opener", rx(r"\bi hope (?:this|you|that)\b[^.\n]{0,40}\b(?:well|good health|finds you)\b"), 5, "Delete. Nobody opens a proposal for this line."),
    ("'I am writing to'", rx(r"\bi am writing to\b"), 5, "Delete and start with their problem."),
    ("excitement claim", rx(r"\bi(?: am|'m) (?:very |really |truly |so |super )?(?:excited|thrilled|delighted|eager|pleased|happy) (?:to|about)\b"), 5, "Claimed enthusiasm reads as template. Show interest by saying something specific about the job."),
    ("'interested in' opener", rx(r"\bi(?: am|'m) (?:very |highly |really )?interested in\b"), 4, "Applying already says you're interested. Use the space for substance."),
    ("'I came across / read your post'", rx(r"\bi (?:came across|stumbled upon|have gone through|went through|have read|carefully read|have reviewed|reviewed|have carefully) (?:your|the|through)\b"), 5, "Prove you read it by using a detail from it, not by saying so."),
    ("thanks for posting", rx(r"\bthank(?:s| you) (?:so much )?for (?:posting|the opportunity|sharing|considering|your time|your consideration)\b"), 4, "Filler. Cut."),
    ("'perfect fit'", rx(r"\b(?:perfect|ideal|great|right|best) (?:fit|match|candidate|person|choice)\b"), 5, "Every bidder says this. Replace with the one proof that makes it true."),
    ("'look no further'", rx(r"\blook no further\b"), 5, "Cut."),
    ("'bring your vision to life'", rx(r"\bbring (?:your )?(?:vision|idea|ideas|project|dream)s? to life\b"), 5, "Cut."),
    ("'next level'", rx(r"\bto the next level\b"), 4, "Cut or say the actual result."),
    ("'hit the ground running'", rx(r"\bhit the ground running\b"), 3, "Say when you can start instead."),
    ("'proven track record'", rx(r"\bproven track record\b"), 5, "Name one result instead."),
    ("experience adjective", rx(r"\b(?:extensive|vast|rich|wealth of|solid|strong|deep|in-depth) (?:experience|expertise|background|knowledge)\b"), 4, "An adjective is not proof. Name the project."),
    ("years-of-experience line", rx(r"\b\d+\+?\s*years?(?:'|’)? (?:of )?(?:professional |hands-on |solid |extensive |industry )?experience\b"), 3, "The client sees your history on the card. Spend the words on their job."),
    ("'I have experience with'", rx(r"\bi have (?:\w+ )?experience (?:with|in|of)\b"), 4, "One vendor dataset ties this phrase to about 3.7 points lower reply rate. Show the project instead."),
    ("'would you be open'", rx(r"\bwould you be open\b"), 4, "Tied to lower replies in one vendor dataset. Ask a direct question about the work."),
    ("call request", rx(r"\b(?:discovery|intro|introductory|quick|brief|short|15[- ]min(?:ute)?|zoom) call\b|\b(?:hop|jump|get) on a call\b|\bschedule a call\b"), 3, "A call is a cost to the client. Ask one question they can answer in a line; let them offer the call."),
    ("'tailored to your needs'", rx(r"\btailored to (?:your|the) (?:needs|requirements|business|goals|project)\b"), 4, "Cut."),
    ("'hire me'", rx(r"\bhire me\b"), 3, "Cut."),
    ("formal sign-off", rx(r"\b(?:best|kind|warm|warmest) regards\b|\bsincerely\b|\byours (?:truly|faithfully)\b|\bthanks (?:&|and) regards\b|\brespectfully\b"), 2, "End on your question. A first name is enough."),
    ("'feel free / don't hesitate'", rx(r"\bfeel free to\b|\b(?:don't|do not) hesitate to\b"), 3, "Cut. End with a specific question."),
    ("'looking forward'", rx(r"\blook(?:ing)? forward to (?:hearing|working|your|collaborating|discussing|the opportunity|connecting)\b"), 3, "Cut. End with a specific question."),
    ("'let me know'", rx(r"\blet me know (?:if|when|what|how|your|should)\b"), 1, "Soft close. A direct question gets answered more often."),
    ("'I am confident'", rx(r"\bi(?: am|'m) confident (?:that|i|in|my)\b"), 4, "Confidence is shown by specifics."),
    ("guarantee boilerplate", rx(r"\brest assured\b|\b100% (?:satisfaction|guarantee|client)\b|\bunlimited revisions\b|\bsatisfaction guaranteed\b|\bon[- ]time delivery\b"), 3, "Mass-bid boilerplate."),
    ("'high-quality work'", rx(r"\b(?:high|top)[- ]quality (?:work|results|service|services|deliverables|code|output)\b"), 3, "Empty claim. Cut."),
    ("'as per your requirements'", rx(r"\bas per (?:your|the) (?:requirement|requirements|job|description|post|needs)\b"), 3, "Cut."),
    ("generic salutation", rx(r"\bdear (?:sir|madam|client|hiring manager|hiring team|recruiter|team)\b|\bgreetings(?: of the day)?[,!]|\brespected (?:sir|client)\b|\bhi there\b|\bhello there\b|\bhello sir\b"), 5, "Use the client's first name if the post or their reviews show it, or no greeting."),
    ("mass-bid marker", rx(r"\bkindly\b|\bdo the needful\b|\bplease revert\b|\bping me\b|\binbox me\b"), 2, "Clients associate these with bulk bids. Use plain 'please' or a direct sentence."),
    ("self-label", rx(r"\bi(?: am|'m) (?:a |an )?(?:passionate|dedicated|seasoned|skilled|experienced|professional|detail[- ]oriented|results[- ]driven|highly skilled|hardworking|creative|versatile)\b"), 4, "Self-applied adjectives. Cut them; keep the fact."),
    ("knocking other freelancers", rx(r"\bmany freelancers\b|\bunlike (?:other|most|many) (?:freelancers|developers|designers|agencies)\b|\bmost freelancers\b"), 4, "Tied to lower replies in one vendor dataset. Talk about the job."),
    ("'not AI' disclaimer", rx(r"\b(?:non[- ]chatgpt|not (?:an? )?(?:ai|chatgpt|bot|robot)\b|human[- ]written|written by (?:a )?(?:real )?human|no ai (?:was )?used|100% human)\b"), 6, "Announcing you are not an AI lowered replies in one vendor dataset and invites doubt. Cut."),
    ("'I understand that you'", rx(r"\bi (?:fully |completely |clearly |totally )?understand (?:that )?(?:you|your|the|what)\b"), 3, "Show understanding with a specific consequence, not the word 'understand'."),
    ("'based on your description'", rx(r"\bbased on (?:your|the) (?:description|requirements|job post|post|brief)\b"), 3, "Cut."),
    ("'I would love to'", rx(r"\bi(?: would|'d) (?:love|like) to (?:help|work|assist|be part|discuss|hear|learn|collaborate|contribute)\b"), 2, "Filler. Say what you'd do first."),
    ("over-assurance", rx(r"\bi can (?:definitely|certainly|surely|easily|absolutely)\b|\b(?:definitely|certainly|absolutely)[!,]"), 3, "Cut the adverb."),
    ("badge restated", rx(r"\btop[- ]rated(?: plus)?\b|\b100% job success\b|\bjob success score\b|\brising talent\b|\bexpert[- ]vetted\b"), 2, "The card already shows your badge and score. Spend the line on their job, or keep it to a clause."),
    ("'that's where I come in'", rx(r"\b(?:that's|this is) where i come in\b|\bhere's the thing\b|\blet's dive in\b|\bwithout further ado\b"), 4, "Sales-page phrasing. Cut."),
]

AI_VOCAB = """delve delves delving leverage leverages leveraged leveraging robust seamless seamlessly pivotal crucial
tapestry testament underscore underscores underscoring showcase showcases showcased showcasing foster fosters
fostering elevate elevates elevating streamline streamlined streamlining cutting-edge comprehensive meticulous
meticulously landscape realm unlock unlocks unlocking harness harnessing empower empowers empowering bespoke holistic
synergy synergies game-changer game-changing top-notch state-of-the-art best-in-class world-class innovative utilize
utilizes utilizing utilise facilitate facilitates intricate intricacies multifaceted paramount endeavor endeavour
moreover furthermore additionally ever-evolving fast-paced user-centric dependable vibrant enhance enhances enhancing
spearheaded spearhead orchestrate orchestrated supercharge supercharged revolutionize revolutionise transformative
elevated effortlessly impactful actionable insightful noteworthy commendable""".split()

AI_PHRASES = [
    rx(r"\bin today's (?:fast-paced|digital|competitive|ever-changing)\b"),
    rx(r"\bnavigat(?:e|ing) the (?:complexit|challeng|intricac)"),
    rx(r"\b(?:a|the) deep dive\b"),
    rx(r"\bvaluable insights?\b"),
    rx(r"\balign(?:s|ed|ing)? (?:perfectly |closely |well )?with\b"),
    rx(r"\bplays? a (?:key|crucial|vital|pivotal|significant) role\b"),
    rx(r"\bit'?s (?:important|worth) (?:to note|noting)\b"),
    rx(r"\bwhen it comes to\b"),
    rx(r"\bat the end of the day\b"),
]

SELF_UNDERMINE = [
    rx(r"\bi(?: am|'m) not (?:presenting|claiming|suggesting|implying|pretending)\b"),
    rx(r"\b(?:do|does|did) not (?:claim|imply|establish)\b|\bdon't (?:want to )?(?:claim|imply|overstate)\b|\bdoes not by itself\b"),
    rx(r"\bi (?:can't|cannot|won't|wouldn't|will not) (?:truthfully |honestly |in good faith )?(?:attribute|claim|present|label|mislabel|verify|promise)\b"),
    rx(r"\b(?:to be|being|i'll be|i will be) (?:fully |completely |totally |perfectly )?(?:honest|transparent|upfront|candid)\b|\bi(?: am|'m) upfront\b|\bfull disclosure\b|\bin full transparency\b|\bi must admit\b"),
    rx(r"\bclosest (?:official|available|verified)\b|\bofficial (?:portfolio|example|profile|highlight|react|next)\b"),
    rx(r"\b(?:should|would) be (?:treated|presented|regarded|read) as\b"),
    rx(r"\bnot a claim\b|\bis not a guarantee\b|\bnot guaranteed\b|\bi can't guarantee\b"),
    rx(r"\bthese (?:highlights|examples|items|projects|samples) (?:verify|support|demonstrate only|do not)\b"),
    rx(r"\bi (?:haven't|have not|have never|never) (?:worked|used|built|done|shipped|had)\b"),
    rx(r"\bi(?: am|'m) not (?:an expert|very familiar|familiar|experienced|an? \w+ (?:expert|specialist))\b|\bno (?:direct|prior|hands-on|real) experience\b|\blimited experience\b"),
    rx(r"\b(?:isn't|is not|it's not|aren't|are not|no longer) (?:currently |publicly |yet )?(?:live|hosted|online|deployed|public|publicly available)\b"),
    rx(r"\balthough i (?:don't|haven't|am not|lack)\b|\bwhile i (?:don't|haven't|am not|lack)\b|\beven though i (?:don't|haven't)\b"),
]

CONTRAST = [
    rx(r"\b(?:is|are|was|were|it's|that's|isn't|aren't|wasn't)\s*(?:not|n't)?\s*(?:just|only|merely|simply)\b[^.?!\n]{0,90}[.,;:—-]\s*(?:it's|it is|but|they're|that's|it was)\b"),
    rx(r"\bnot (?:just|only|merely)\b[^.?!\n]{0,70}\bbut\b"),
    rx(r"\b(?:is|are|was|isn't|aren't|it's)\s*(?:not|n't) (?:a|an|the|about)\b[^.?!\n]{0,60}[.,;—-]\s*(?:it's|it is|but|they're)\b"),
    rx(r",\s+not\s+(?:a|an|the|in|on|by|as|to|just|for|from|with|your|my)\b"),
    rx(r"\brather than\b"),
    rx(r"\bless about\b[^.?!\n]{0,40}\bmore about\b"),
]

PARTICIPLE_TAIL = rx(r",\s+(?:ensuring|enabling|allowing|making|providing|resulting|helping|giving|creating|delivering|driving|keeping|leaving|reducing|improving|boosting|maximizing|minimizing|guaranteeing)\b")
THREE_LIST = rx(r"\b[\w./+#-]+,\s+[\w./+#-]+(?:\s[\w./+#-]+)?,?\s+and\s+[\w./+#-]+")
HEDGES = rx(r"\b(?:might|may|could|perhaps|possibly|potentially|generally|typically|usually|often|likely|probably|somewhat|fairly|relatively|arguably)\b")
INTENSIFIERS = rx(r"\b(?:seamlessly|effortlessly|efficiently|effectively|successfully|significantly|extremely|highly|truly|incredibly|thoroughly|carefully|deeply|greatly)\b")
CONTRACTION = rx(r"\b\w+(?:n't|'m|'d|'ll|'ve|'re)\b|\b(?:it|that|there|here|what|who|let)'s\b")
EMOJI = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF✅✔⭐]")
URL = rx(r"https?://\S+|\bwww\.\S+|\b[\w-]+\.(?:com|io|ai|co|dev|app|net|org|me|design|studio|xyz|tech)\b(?:/\S*)?")
NUMBER_PROOF = rx(r"\b\d[\d,.]*\s?(?:%|x\b|k\b|ms\b|sec\b|seconds?\b|min\b|minutes?\b|hours?\b|days?\b|weeks?\b|months?\b|users?\b|pages?\b|screens?\b|clients?\b|customers?\b|orders?\b|requests?\b|records?\b|rows?\b|stores?\b|sites?\b|commits?\b|features?\b|stars?\b|reviews?\b|fps\b)|[$€£]\s?\d")
SHOWN_PROOF = rx(r"\b(?:report|file|screenshots?|video|recording|portfolio item|sample|samples|pdf|it|them) (?:is |are )?attached\b|\battached (?:is|are|a|an|the|my|from|below)\b|\bi(?:'ve| have) attached\b|\bportfolio\b|\bon my profile\b|\bloom\b|\bvideo walkthrough\b|\bscreenshots?\b|\bcase study\b|\b5[- ]star\b|\breview\b|\bgithub\b|\blive at\b|\bdemo\b")
SOFT_CLOSE = rx(r"\blet me know\b|\blook(?:ing)? forward\b|\bfeel free\b|\bhesitate\b|\bhappy to (?:discuss|chat|talk|help|answer|jump|hop|share)\b|\bthank(?:s| you)\b|\bregards\b|\bavailable (?:to|for) (?:discuss|a call|chat)\b|\bhope to hear\b")
SEE_ABOVE = rx(r"\b(?:see|as (?:mentioned|stated|noted)|refer to|per) (?:above|my (?:cover letter|proposal|profile)|the cover letter|below)\b|\bas (?:mentioned|stated) (?:above|earlier|in my)\b")

GREETING = rx(r"^\s*(?:hi|hello|hey|dear|greetings|good (?:day|morning|afternoon|evening))\b(?:[ \t]+[\w.'-]+){0,3}[ \t]*[,!:\n-]")
SELF_INTRO = rx(r"^\s*(?:my name is|i am|i'm|i have|i've|i work|i specialize|i specialise|as an?|with (?:over |more than )?\d+|having \d+|this is|we are|we're|our (?:team|agency|company))\b")
ECHO = rx(r"^\s*(?:you(?:'re| are)? (?:need|want|looking|seeking|require|after|trying)|you (?:need|want|require|mentioned|said|listed|asked)|your (?:brief|job post|post|posting|project|description|requirements?) (?:covers|requires|describes|mentions|says|asks|is|needs|outlines|calls)|it (?:sounds|looks|seems) like you|as per your|from your (?:description|post|brief))\b")
STOCK_OPEN = rx(r"^\s*(?:i (?:just )?(?:read|came across|stumbled upon|noticed|reviewed|went through|have read|have gone through)\b|i(?: am|'m) (?:very |really |so )?(?:interested|excited|thrilled|confident|writing|glad|happy)\b|thank(?:s| you)\b|i hope\b|i understand\b|i can (?:help|do|build|complete|assist|definitely|deliver)\b|i(?: would|'d) (?:love|like)\b|i believe\b|are you looking\b|looking for\b|this (?:project|job|role|position|opportunity) (?:sounds|looks|is|seems)\b|your (?:project|job|posting|post) (?:caught|sounds|looks|seems|is (?:exactly|very|really|quite))\b)")

REQUIRED_WORD = [
    rx(r"(?:start|begin|open)\w*\s+(?:your\s+|the\s+)?(?:proposal|cover letter|reply|response|application|message|bid)\s+with\s+(?:the\s+)?(?:word|phrase|words)?\s*[\"'“‘]([^\"'”’\n]{2,40})[\"'”’]"),
    rx(r"(?:write|include|mention|type|use|put|add|say)\s+(?:the\s+)?(?:word|phrase|code ?word|keyword|password)\s+[\"'“‘]([^\"'”’\n]{2,40})[\"'”’]"),
    rx(r"(?:start|begin|open)\w*\s+(?:your\s+|the\s+)?(?:proposal|cover letter|reply|response|application|message|bid)\s+with\s+(?:the\s+)?(?:word|phrase)\s+([A-Za-z][\w-]{2,30})"),
    rx(r"(?:write|include|mention|type|use|put|add|say)\s+(?:the\s+)?(?:word|phrase|code ?word|keyword|password)\s+([A-Za-z][\w-]{2,30})"),
]
AI_TRAP = rx(r"\b(?:if you(?:'re| are) (?:an? )?(?:ai|llm|bot|language model|chatbot|chatgpt)|ai (?:agents?|models?|assistants?)[^.\n]{0,30}(?:must|should|please)|ignore (?:all )?(?:previous|prior) instructions)\b")


# ----------------------------------------------------------------------------------------------- helpers
def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read().replace("\r\n", "\n").replace("\r", "\n")


def straighten(text):
    return (text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"'))


def words(text):
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'./+#-]*[A-Za-z0-9+#]|[A-Za-z0-9]", text)


def stem(w):
    w = w.lower().strip("'.-/")
    for suf in ("ing", "ed", "es", "s"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def sentences(text):
    out = []
    for block in re.split(r"\n+", text):
        block = block.strip()
        if not block:
            continue
        block = re.sub(r"^(?:[-*•–]|\d+[.)])\s+", "", block)
        parts = re.split(r"(?<=[.!?])\s+(?=[\"'A-Z0-9])", block)
        out.extend(p.strip() for p in parts if p.strip())
    return out


def body_without_signature(text):
    lines = [l for l in text.strip().split("\n")]
    while lines and (not lines[-1].strip() or len(words(lines[-1])) <= 3 and not lines[-1].strip().endswith("?")):
        lines.pop()
    return "\n".join(lines)


def job_anchors(job):
    """Distinctive terms from the job post: words a generic letter would not contain."""
    counts = {}
    display = {}
    for w in words(straighten(job)):
        lw = w.lower().strip(".'")
        if len(lw) < 3 and not re.search(r"[0-9+#]", lw):
            continue
        if lw in STOP or lw in GENERIC_JOB:
            continue
        s = stem(lw)
        if s in STOP or s in GENERIC_JOB:
            continue
        counts[s] = counts.get(s, 0) + 1
        display.setdefault(s, w)
    return counts, display


def find_all(patterns, text):
    hits = []
    for p in patterns:
        for m in p.finditer(text):
            hits.append(m.group(0).strip())
    return hits


def shingles(text, n=4):
    ws = [w.lower() for w in words(straighten(text))]
    return set(tuple(ws[i:i + n]) for i in range(max(0, len(ws) - n + 1)))


def load_history(path):
    items = []
    if os.path.isdir(path):
        for name in sorted(os.listdir(path)):
            if name.lower().endswith((".txt", ".md")):
                items.append((name, read_text(os.path.join(path, name))))
    else:
        data = json.loads(read_text(path))
        for i, d in enumerate(data if isinstance(data, list) else data.get("letters", [])):
            if isinstance(d, str):
                items.append(("history[%d]" % i, d))
            elif isinstance(d, dict):
                t = d.get("cover_letter") or d.get("text") or d.get("letter") or ""
                items.append((str(d.get("title") or d.get("job_id") or "history[%d]" % i), t))
    return items


# ----------------------------------------------------------------------------------------------- the lint
def lint(proposal, job=None, answers=None, history=None):
    raw = proposal.strip()
    text = straighten(raw)
    low = text.lower()
    job_text = straighten(job) if job else ""
    job_low = job_text.lower()
    res = {"blockers": [], "preview": [], "fit": [], "voice": [], "notes": [], "confirm": []}
    score = {"preview": 100, "fit": 100, "voice": 100}

    def add(section, level, msg, pts=0):
        res[section].append({"level": level, "msg": msg})
        if section in score:
            score[section] -= pts

    # A post that lists numbered items to include ("1. Your rate 2. Your start date ...") earns a
    # numbered reply of the same size, so list and length limits relax for it.
    job_numbered = len(re.findall(r"^\s*\d+[.)]\s+\S", job_text, re.M)) if job_text else 0
    long_warn, long_bad = (300, 400) if job_numbered >= 4 else (220, 300)

    ws = words(text)
    n_words = len(ws)
    sents = sentences(text)
    slens = [len(words(s)) for s in sents if len(words(s)) > 0]

    # ---------------- required code word / AI trap in the job post
    required = None          # a code word meant for humans
    trap_words = []          # words an AI trap asks for
    if job_text:
        any_trap = False
        for js in re.split(r"(?<=[.!?])\s+|\n+", job_text):
            is_trap = bool(AI_TRAP.search(js))
            any_trap = any_trap or is_trap
            for p in REQUIRED_WORD:
                m = p.search(js)
                if m:
                    word = m.group(1).strip().strip(".,;:!")
                    if is_trap:
                        trap_words.append(word)
                    elif required is None:
                        required = word
                    break
        for tw in trap_words:
            if re.search(r"(?<!\w)%s(?!\w)" % re.escape(tw.lower()), low[:300]):
                res["blockers"].append({"name": "AI trap triggered",
                                        "detail": "The post tells AI tools to use '%s'. It is in your text. A person who read the post leaves it out." % tw,
                                        "found": [tw]})
            else:
                add("notes", "ok", "The post contains an AI trap ('%s'). Your text correctly leaves it out." % tw)
        if required:
            if required.lower() not in low:
                res["blockers"].append({"name": "Required code word missing",
                                        "detail": "The post asks for '%s' in the proposal. It is not there. Clients use this to discard bids unread." % required,
                                        "found": []})
            elif required.lower() not in low[:120]:
                add("fit", "warn", "The post asks for the word '%s'. It is in your text but not at the start, where the client looks for it." % required, 8)
            else:
                add("notes", "ok", "Code word '%s' is at the start, as the post asked." % required)
        if any_trap and not trap_words:
            add("notes", "warn", "The post contains wording aimed at AI tools. Read it yourself and check you did not follow an instruction meant to catch bots.")

    # ---------------- blockers
    for name, pat, advice in BLOCKERS:
        found = [m.group(0).strip()[:80] for m in pat.finditer(raw)]
        if found:
            res["blockers"].append({"name": name, "detail": advice, "found": found[:4]})
    plain_utm = re.findall(r"[?&]utm_[a-z]+=[^\s&]*", raw)
    if plain_utm and not any(b["name"].startswith("AI-tool") for b in res["blockers"]):
        add("voice", "warn", "A link carries tracking tags (%s). Paste clean links." % plain_utm[0][:40], 5)

    # ---------------- preview
    opening_text = text
    code_line = ""
    first_line = text.split("\n", 1)[0].strip()
    if required and first_line.lower().strip(" .!:-") == required.lower() and "\n" in text:
        code_line = first_line
        opening_text = text.split("\n", 1)[1].strip()
    preview = re.sub(r"\s+", " ", text)[:PREVIEW_CHARS]
    preview_safe = re.sub(r"\s+", " ", text)[:PREVIEW_SAFE]

    after_greeting = opening_text
    g = GREETING.match(opening_text)
    if g:
        greet = g.group(0).strip()
        if re.search(r"\b(?:there|sir|madam|client|hiring|team|recruiter|everyone|all)\b", greet, re.I) or re.match(r"^\s*(?:greetings|good (?:day|morning|afternoon|evening)|dear)\b", greet, re.I):
            add("preview", "bad", "Generic greeting (\"%s\") spends the preview on nothing. Use the client's first name or start with the point." % greet, 20)
        else:
            add("preview", "info", "Greeting \"%s\" uses %d of ~%d preview characters. Fine if that is really the client's name." % (greet, len(greet), PREVIEW_CHARS))
        after_greeting = opening_text[g.end():].strip()
    first_sent = sentences(after_greeting)[0] if sentences(after_greeting) else ""
    fs_words = len(words(first_sent))
    if SELF_INTRO.match(after_greeting):
        add("preview", "bad", "Opens with you (\"%s...\"). The client is scanning for their own project. Open with their problem, a detail from their post, or your closest proof." % first_sent[:60], 40)
    elif STOCK_OPEN.match(after_greeting):
        add("preview", "bad", "Stock opener (\"%s...\"). It could sit on top of any proposal, so it gets skipped." % first_sent[:60], 35)
    elif ECHO.match(after_greeting):
        add("preview", "warn", "Opens by repeating the brief back (\"%s...\"). The client already knows what they asked for. Add what it means: a risk, a decision, or the first step." % first_sent[:60], 22)
    elif re.match(r"^\s*i\b", after_greeting, re.I):
        add("preview", "warn", "First sentence starts with \"I\". It can work if it is your closest proof; otherwise lead with their situation.", 8)
    if first_sent.endswith("?"):
        add("preview", "ok", "Opens with a question. Question openers were about six times more common among top-quartile bidders in one vendor dataset.")
    if fs_words > 34:
        add("preview", "warn", "First sentence is %d words. The preview cuts it mid-thought. Get one complete idea into the first 20 or so words." % fs_words, 10)
    if code_line:
        add("preview", "info", "Code word line \"%s\" comes first, as the post asked. The preview then continues with your first real sentence." % code_line)

    # ---------------- anchors (needs the job post)
    anchors_used = []
    generic_sents = []
    if job_text:
        counts, display = job_anchors(job_text)
        for cw in trap_words + ([required] if required else []):   # instruction words are not job details
            for part in words(cw):
                counts.pop(stem(part), None)
        prop_stems = set(stem(w) for w in ws)
        prev_stems = set(stem(w) for w in words(preview))
        anchors_used = sorted((s for s in counts if s in prop_stems), key=lambda s: -counts[s])
        anchors_preview = [s for s in anchors_used if s in prev_stems]
        shown = ", ".join(display[s] for s in anchors_used[:12]) or "none"
        if len(anchors_used) < 3:
            add("fit", "bad", "Only %d term(s) from the job post appear in your text (%s). It reads as written without the post open." % (len(anchors_used), shown), 25)
        elif len(anchors_used) < 5:
            add("fit", "warn", "Only %d terms from the job post appear in your text (%s). Use more of the client's own details." % (len(anchors_used), shown), 10)
        else:
            add("fit", "ok", "%d distinct terms from the job post appear in your text (%s)." % (len(anchors_used), shown))
        if not anchors_preview:
            add("preview", "bad", "Nothing from the job post appears in the first %d characters. The client cannot tell from the preview that this is about their job." % PREVIEW_CHARS, 25)
        else:
            add("preview", "ok", "Preview contains the job's own terms: %s." % ", ".join(display[s] for s in anchors_preview[:6]))
        anchor_set = set(anchors_used)
        body_sents = sentences(body_without_signature(text))
        for s in body_sents:
            sw = words(s)
            if len(sw) < 7:          # short sentences are connective tissue, not claims
                continue
            lw = [w.lower() for w in sw]
            has_anchor = any(stem(w) in anchor_set for w in sw)
            specific = bool(re.search(r"\d", s) or URL.search(s) or '"' in s
                            or any(w in NUMBER_WORDS for w in lw)
                            or re.search(r"(?<!^)(?<![.!?]\s)\b[A-Z][a-z]+[A-Z]?\w*", s))
            rare = [w for w in lw if len(w) > 2 and w not in STOP and w not in GENERIC_JOB and w not in COMMON
                    and stem(w) not in GENERIC_JOB and stem(w) not in COMMON]
            stock_hit = any(p.search(s) for _, p, pts, _ in STOCK if pts >= 4)
            if stock_hit or (not has_anchor and not specific and len(rare) < 3):
                generic_sents.append(s)
        if body_sents:
            ratio = len(generic_sents) / float(len(body_sents))
            if ratio > 0.5:
                add("fit", "bad", "%d of %d sentences contain nothing from this job and no concrete detail. They could be pasted under any post (swap test)." % (len(generic_sents), len(body_sents)), 25)
            elif ratio > 0.34:
                add("fit", "warn", "%d of %d sentences are generic enough to paste under another job (swap test)." % (len(generic_sents), len(body_sents)), 12)
        job_words = len(words(job_text))
        if job_words < 70 and n_words > 150:
            add("fit", "warn", "The client wrote %d words; you wrote %d. Match their effort: 60 to 100 words is plenty here." % (job_words, n_words), 10)
        for s in sentences(job_text):
            if s.endswith("?") and len(words(s)) >= 4:
                res["confirm"].append(s[:160])
        res["confirm"] = res["confirm"][:8]
    else:
        add("notes", "info", "No job post given, so the job-specific checks (anchors, swap test, code word) did not run. Pass --job for the full lint.")

    # ---------------- fit: length, proof, close, balance
    if n_words < 45:
        add("fit", "warn", "%d words. Too thin to show a proof and a first step, unless the post itself is one line." % n_words, 10)
    elif n_words > long_bad:
        add("fit", "bad", "%d words. Most clients stop long before this. Aim for 80 to 180, up to about 220 for a detailed expert brief." % n_words, 20)
    elif n_words > long_warn:
        add("fit", "warn", "%d words. Long. Aim for 80 to 180 unless the brief is detailed and expert-level." % n_words, 10)
    elif job_numbered >= 4 and n_words > 220:
        add("fit", "ok", "%d words. Longer than usual, which is fine here: the post asks for %d numbered items." % (n_words, job_numbered))
    else:
        add("fit", "ok", "%d words." % n_words)

    urls = URL.findall(text)
    has_number = bool(NUMBER_PROOF.search(text))
    has_shown = bool(SHOWN_PROOF.search(text))
    if not urls and not has_number and not has_shown:
        add("fit", "bad", "No link, number, attachment or review is mentioned. The proof is asserted, not shown. Add one checkable thing.", 20)
    elif not urls and not has_shown:
        add("fit", "warn", "No link or attached item is mentioned. Give the client one thing they can open.", 8)
    if len(urls) > 3:
        add("fit", "warn", "%d links. One or two that go straight to the relevant work beat a list." % len(urls), 5)

    body = body_without_signature(text)
    bsents = sentences(body)
    last = bsents[-1] if bsents else ""
    q_count = text.count("?")
    closing_q = next((s for s in reversed(bsents[-2:]) if s.endswith("?")), None)
    if closing_q:
        add("fit", "ok", "Ends with a question: \"%s\"" % closing_q[:110])
    elif SOFT_CLOSE.search(" ".join(bsents[-2:])):
        add("fit", "warn", "Soft close (\"%s\"). End with one specific question the client can answer in a line." % last[:80], 10)
    else:
        add("fit", "warn", "Ends without a question or a concrete next step.", 8)
    if q_count > 2:
        add("fit", "warn", "%d questions. Pick the one that changes the scope or the price." % q_count, 5)

    i_count = len(re.findall(r"\b(?:i|i'm|i've|i'd|i'll|my|me|mine|myself)\b", low))
    you_count = len(re.findall(r"\b(?:you|your|you're|you'd|you'll|you've|yours)\b", low))
    you_ratio = you_count / float(max(1, you_count + i_count))
    if n_words >= 60 and you_ratio < 0.2:
        add("fit", "warn", "\"I/my\" appears %d times, \"you/your\" %d. The letter is about you. Turn some sentences around to their project." % (i_count, you_count), 10)
    i_starts = sum(1 for s in sents if re.match(r"^(?:i|i'm|i've|i'd|i'll|my)\b", s, re.I))
    if len(sents) >= 5 and i_starts / float(len(sents)) > 0.5:
        add("voice", "warn", "%d of %d sentences start with I or My." % (i_starts, len(sents)), 6)

    money = re.findall(r"[$€£]\s?\d[\d,]*", text)
    if len(money) >= 4:
        add("fit", "warn", "%d price figures in the letter. A price table belongs in the milestone fields or a later message; one line on what the bid covers is enough." % len(money), 6)

    # ---------------- voice
    stock_pts = 0
    for label, pat, pts, advice in STOCK:
        found = [m.group(0) for m in pat.finditer(text)]
        if found:
            stock_pts += pts * min(2, len(found))
            add("voice", "bad" if pts >= 4 else "warn", "%s: \"%s\". %s" % (label, found[0], advice))
    score["voice"] -= min(40, stock_pts)

    vocab_hits = []
    for w in AI_VOCAB:
        if re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(w), low) and not (job_low and re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(w), job_low)):
            vocab_hits.append(w)
    for p in AI_PHRASES:
        m = p.search(text)
        if m and not (job_low and m.group(0).lower() in job_low):
            vocab_hits.append(m.group(0).lower())
    if vocab_hits:
        add("voice", "bad" if len(vocab_hits) >= 3 else "warn", "AI-flavoured vocabulary: %s. Swap for the plain word (use, build, fix, strong, important) or cut." % ", ".join(sorted(set(vocab_hits))), min(24, 4 * len(set(vocab_hits))))

    under = find_all(SELF_UNDERMINE, text)
    if under:
        add("voice", "bad" if len(under) >= 2 else "warn",
            "%d self-undermining or disclaimer phrase(s): %s. Each one argues against you. If the gap matters, state it once in plain words and say what you'd do about it; if it is a core requirement, skip the job." % (len(under), "; ".join('"%s"' % u for u in under[:4])),
            min(30, 9 * len(under)))

    contrast = find_all(CONTRAST, text)
    if len(contrast) >= 2:
        add("voice", "warn", "Contrast framing used %d times (\"X, not Y\" / \"isn't just X, it's Y\" / \"rather than\"): %s. One is fine. Repeated, it is the most recognisable machine rhythm. Say the positive claim directly." % (len(contrast), "; ".join('"%s"' % c[:45] for c in contrast[:3])), min(18, 5 * len(contrast)))

    tails = PARTICIPLE_TAIL.findall(text)
    if len(tails) >= 2:
        add("voice", "warn", "%d sentences end in a trailing \"-ing\" clause (\", ensuring...\", \", making...\"). Split them or cut the tail." % len(tails), 6)

    emdash = raw.count("—") + raw.count(" -- ")
    if emdash >= 3:
        add("voice", "warn", "%d em dashes. Few people type them in a proposal box. Use a comma, a full stop or brackets." % emdash, 8)
    elif emdash >= 1:
        add("voice", "info", "%d em dash(es). Harmless once, but most people type a comma or a hyphen." % emdash, 2)

    semis = text.count(";")
    if semis >= 2:
        add("voice", "info", "%d semicolons. Rare in typed messages; a full stop reads more natural." % semis, 3)

    curly = sum(raw.count(c) for c in "’‘“”")
    if curly:
        add("voice", "info", "%d curly quote(s)/apostrophe(s). Text typed into Upwork has straight ones; curly ones suggest a paste from a chatbot or a word processor. Retype or replace them." % curly, 3)

    bullets = [l for l in text.split("\n") if re.match(r"^\s*(?:[-*•–]|\d+[.)])\s+\S", l)]
    label_bullets = [l for l in bullets if re.match(r"^\s*(?:[-*•–]|\d+[.)])\s+[A-Z][\w /&+-]{1,28}:\s", l)]
    if job_numbered >= 3 and 4 < len(bullets) <= job_numbered + 1:
        add("voice", "ok", "%d list lines, matching the %d numbered items the post asked for." % (len(bullets), job_numbered))
    elif len(bullets) > 4:
        add("voice", "warn", "%d bullet lines. Long bullet lists make a letter look templated, and bullets were less common among top-quartile bidders in one vendor dataset. Keep at most three, or write two sentences." % len(bullets), 8)
    if len(label_bullets) >= 2:
        add("voice", "warn", "%d bullets start with a Label: followed by text. That layout is a chatbot habit. Write them as plain sentences." % len(label_bullets), 6)

    header_lines = [l.strip() for l in text.split("\n")
                    if re.match(r"^\s*[A-Z][\w '&/-]{2,34}:\s*$", l) and len(words(l)) <= 4
                    and not re.search(r"\b(?:i|i'd|i'll|i've|you|your|we)\b", l, re.I)]
    if header_lines:
        add("voice", "warn", "Section header line(s) in a cover letter: %s. A message to a person has no headers." % ", ".join('"%s"' % h for h in header_lines[:3]), 8)

    emojis = EMOJI.findall(raw)
    if emojis:
        add("voice", "bad" if EMOJI.match(raw.lstrip()[:2] or " ") else "warn", "%d emoji. Emoji openers were about half as common among top-quartile bidders in one vendor dataset." % len(emojis), 8)

    exclam = text.count("!")
    if exclam >= 2:
        add("voice", "info", "%d exclamation marks." % exclam, 3 if exclam < 4 else 6)

    caps = [w for w in re.findall(r"\b[A-Z]{4,}\b", text) if w not in ACRONYM_OK and w.lower() not in job_low and (not required or w.lower() not in required.lower())]
    if len(caps) >= 2:
        add("voice", "info", "Words in capitals: %s." % ", ".join(sorted(set(caps))[:5]), 3)

    n_contr = len(CONTRACTION.findall(text))
    if n_words >= 80 and n_contr == 0:
        add("voice", "warn", "No contractions in %d words (I am, I would, do not). People write I'm, I'd, don't." % n_words, 8)

    three = THREE_LIST.findall(text)
    if len(three) >= 4:
        add("voice", "info", "%d three-item lists (\"a, b and c\"). Vary them: sometimes two things, sometimes one." % len(three), 4)

    hedges = HEDGES.findall(text)
    if n_words >= 60 and len(hedges) / float(n_words) > 0.035:
        add("voice", "info", "%d hedging words (might, could, usually, likely...). Keep the hedge only where you truly have not seen the code or assets." % len(hedges), 4)

    intens = INTENSIFIERS.findall(text)
    if len(intens) >= 3:
        add("voice", "info", "%d intensifier adverbs (%s). Cut most." % (len(intens), ", ".join(sorted(set(i.lower() for i in intens))[:5])), 4)

    if len(slens) >= 6:
        mean = statistics.mean(slens)
        cv = statistics.pstdev(slens) / mean if mean else 0
        if cv < 0.35:
            add("voice", "warn", "Sentences are all about the same length (average %.0f words, variation %.2f). Mix in a short one. Break a long one." % (mean, cv), 8)
        if min(slens) > 6:
            add("voice", "info", "No sentence of six words or fewer. One short, flat sentence makes the rest sound spoken.", 3)
    long_s = [s for s in sents if len(words(s)) > 38]
    if long_s:
        add("voice", "info", "%d sentence(s) over 38 words. Example: \"%s...\"" % (len(long_s), long_s[0][:70]), 3)

    paras = [p for p in re.split(r"\n\s*\n", text) if len(words(p)) > 12]
    if len(paras) >= 3:
        pl = [len(words(p)) for p in paras]
        if (max(pl) - min(pl)) / float(max(pl)) < 0.2:
            add("voice", "info", "All %d paragraphs are nearly the same size. Uneven blocks look written, even blocks look generated." % len(paras), 3)

    # ---------------- screening answers
    if answers:
        blocks = [b.strip() for b in re.split(r"\n\s*---+\s*\n", straighten(answers)) if b.strip()]
        add("notes", "info", "%d screening answer(s), %d words in total. On jobs with questions, clients commonly see the answers before the cover letter, so answer 1 is your real opening line." % (len(blocks), sum(len(words(b)) for b in blocks)))
        for i, b in enumerate(blocks, 1):
            if SEE_ABOVE.search(b):
                add("fit", "bad", "Answer %d points elsewhere (\"see above / my cover letter\"). Answer in place; the client may read only this box." % i, 10)
            bw = len(words(b))
            if bw > 170:
                add("fit", "warn", "Answer %d is %d words. Put the direct answer in the first sentence and keep it near 40 to 120 words unless the question asks for depth." % (i, bw), 4)
            u = find_all(SELF_UNDERMINE, b)
            if u:
                add("voice", "warn", "Answer %d contains self-undermining wording (%s). If the honest answer to a required question is no, this job is a skip." % (i, "; ".join('"%s"' % x for x in u[:2])), 6)
            for name, pat, advice in BLOCKERS:
                f = [m.group(0).strip()[:80] for m in pat.finditer(b)]
                if f:
                    res["blockers"].append({"name": "%s (answer %d)" % (name, i), "detail": advice, "found": f[:3]})
            for label, pat, pts, advice in STOCK:
                m = pat.search(b)
                if m and pts >= 4:
                    add("voice", "warn", "Answer %d, %s: \"%s\"." % (i, label, m.group(0)), 2)

    # ---------------- history
    if history:
        mine = shingles(text)
        for name, old in history:
            if not old.strip() or straighten(old).strip() == text:
                continue
            other = shingles(old)
            if not mine or not other:
                continue
            overlap = len(mine & other) / float(len(mine))
            first_a = " ".join(words(text)[:12]).lower()
            first_b = " ".join(words(straighten(old))[:12]).lower()
            if overlap > 0.2:
                add("voice", "warn", "%.0f%% of this letter's phrasing also appears in \"%s\". Reused blocks are how clients spot a template." % (100 * overlap, name[:50]), 8)
            elif first_a == first_b:
                add("preview", "warn", "Same opening words as \"%s\"." % name[:50], 10)

    for k in score:
        score[k] = max(0, min(100, score[k]))
    stats = {
        "words": n_words, "sentences": len(slens),
        "avg_sentence_words": round(statistics.mean(slens), 1) if slens else 0,
        "shortest": min(slens) if slens else 0, "longest": max(slens) if slens else 0,
        "variation": round(statistics.pstdev(slens) / statistics.mean(slens), 2) if len(slens) > 1 else 0,
        "i_my": i_count, "you_your": you_count, "questions": q_count, "contractions": n_contr,
        "em_dashes": emdash, "bullets": len(bullets), "links": len(urls),
        "job_terms_used": len(anchors_used), "generic_sentences": len(generic_sents),
    }
    if res["blockers"]:
        verdict = "DO NOT SEND: fix the blockers first."
    elif min(score.values()) >= 85:
        verdict = "Mechanically clean. Now run the fit and voice checklists by hand; they cover what a script cannot judge."
    else:
        worst = min(("preview", "fit", "voice"), key=lambda k: score[k])   # ties go to the earlier gate
        verdict = {
            "preview": "Start with the first two sentences. Most clients decide from the preview, so nothing else matters until it earns the click.",
            "fit": "The letter is not tied tightly enough to this job. Fix fit before polishing wording.",
            "voice": "The content holds up; the wording gives it away. Work through the VOICE list.",
        }[worst]
    return {"verdict": verdict, "scores": score, "preview_200": preview, "preview_150": preview_safe,
            "stats": stats, "generic_sentences": generic_sents[:8], "result": res}


# ----------------------------------------------------------------------------------------------- output
MARK = {"bad": "[X]", "warn": "[!]", "info": "[i]", "ok": "[ok]"}


def render(out):
    L = []
    L.append("UPWORK PROPOSAL LINT   (mechanical checks only: not an AI detector, not a quality verdict)")
    L.append("")
    L.append("WHAT THE CLIENT SEES BEFORE CLICKING")
    L.append("  first 150 chars: \"%s\"" % out["preview_150"])
    L.append("  first 200 chars: \"%s\"" % out["preview_200"])
    L.append("")
    r = out["result"]
    if r["blockers"]:
        L.append("BLOCKERS (fix before sending)")
        for b in r["blockers"]:
            L.append("  [X] %s. %s" % (b["name"], b["detail"]))
            for f in b.get("found", []):
                L.append("        found: %s" % f)
        L.append("")
    for key, title in (("preview", "PREVIEW"), ("fit", "FIT"), ("voice", "VOICE")):
        L.append("%-8s %d/100" % (title, out["scores"][key]))
        items = r[key] or [{"level": "ok", "msg": "Nothing flagged."}]
        for it in items:
            L.append("  %-4s %s" % (MARK.get(it["level"], "[i]"), it["msg"]))
        L.append("")
    if out["generic_sentences"]:
        L.append("SENTENCES THAT WOULD FIT ANY JOB (swap test)")
        for s in out["generic_sentences"]:
            L.append("  - %s" % s[:150])
        L.append("")
    if r["confirm"]:
        L.append("QUESTIONS IN THE JOB POST: confirm by hand that each is answered")
        for c in r["confirm"]:
            L.append("  - %s" % c)
        L.append("")
    if r["notes"]:
        L.append("NOTES")
        for it in r["notes"]:
            L.append("  %-4s %s" % (MARK.get(it["level"], "[i]"), it["msg"]))
        L.append("")
    s = out["stats"]
    L.append("NUMBERS")
    L.append("  words %d | sentences %d | avg %s words | shortest %d | longest %d | variation %s" % (
        s["words"], s["sentences"], s["avg_sentence_words"], s["shortest"], s["longest"], s["variation"]))
    L.append("  I/my %d | you/your %d | questions %d | contractions %d | em dashes %d | bullets %d | links %d" % (
        s["i_my"], s["you_your"], s["questions"], s["contractions"], s["em_dashes"], s["bullets"], s["links"]))
    L.append("")
    L.append("VERDICT  " + out["verdict"])
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="Mechanical checks for an Upwork proposal.")
    ap.add_argument("--proposal", help="path to the cover letter text ('-' for stdin)")
    ap.add_argument("--proposal-text", help="cover letter text given inline")
    ap.add_argument("--job", help="path to the job post text")
    ap.add_argument("--job-text", help="job post text given inline")
    ap.add_argument("--answers", help="path to screening answers, blocks separated by a line of ---")
    ap.add_argument("--history", help="folder of past letters (.txt) or a JSON list")
    ap.add_argument("--json", action="store_true", help="print JSON")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if a.proposal_text:
        proposal = a.proposal_text
    elif a.proposal == "-":
        proposal = sys.stdin.read()
    elif a.proposal:
        proposal = read_text(a.proposal)
    else:
        ap.error("give --proposal FILE or --proposal-text TEXT")
    if not proposal.strip():
        ap.error("the proposal is empty")
    job = a.job_text if a.job_text else (read_text(a.job) if a.job else None)
    answers = read_text(a.answers) if a.answers else None
    history = load_history(a.history) if a.history else None
    out = lint(proposal, job, answers, history)
    print(json.dumps(out, indent=2, ensure_ascii=False) if a.json else render(out))
    return 1 if out["result"]["blockers"] else 0


if __name__ == "__main__":
    sys.exit(main())
