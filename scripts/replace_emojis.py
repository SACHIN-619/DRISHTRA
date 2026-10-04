import re

file_path = "frontend/src/components/Sidebar.tsx"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

replacements = {
    "<span>📊</span>": "<BarChart2 size={16} />",
    "<span>📁</span>": "<Folder size={16} />",
    "<span>⚡</span>": "<Zap size={16} />",
    "<span>🗄️</span>": "<Database size={16} />",
    "<span>🧠</span>": "<Brain size={16} />",
    "<span>🛡️</span>": "<Shield size={16} />",
    "<span>🕸️</span>": "<Share2 size={16} />",
    "<span>🧬</span>": "<Dna size={16} />",
    "<span>🛰️</span>": "<ShieldAlert size={16} />",
    "<span>🔍</span>": "<Search size={16} />",
    "<span>🎯</span>": "<Target size={16} />",
    "<span>⚖️</span>": "<Scale size={16} />",
    "<span>⛓️</span>": "<LinkIcon size={16} />",
    "<span>⚙️</span>": "<Settings size={16} />",
    "<span>🚀</span>": "<Rocket size={16} />"
}

for emoji, icon in replacements.items():
    content = content.replace(emoji, icon)

imports = """import { 
  BarChart2, Folder, Zap, Database, Brain, 
  Shield, Share2, Dna, ShieldAlert, Search, 
  Target, Scale, Link as LinkIcon, Settings, Rocket 
} from 'lucide-react';\n"""

content = content.replace("import { usePathname } from 'next/navigation';", 
                          "import { usePathname } from 'next/navigation';\n" + imports)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
