#!/usr/bin/env python3
"""AI电商主图专家 - 自动安装脚本
用法：python3 install_agent.py
"""
import os, sys, re, json, uuid, time, shutil, zipfile, urllib.request

ZIP_URL = "https://cdn.jsdelivr.net/gh/Kellerhub2/ai-ecommerce-main-image-expert@main/ai_main_image_expert.zip"
AGENT_NAME = "AI电商主图专家"

def get_account_id():
    """从环境路径提取当前账户ID"""
    home = os.path.expanduser("~")
    accounts_dir = os.path.join(home, ".accio", "accounts")
    if not os.path.exists(accounts_dir):
        raise Exception(f"未找到 .accio/accounts 目录，请确认 Accio Work 已安装")
    dirs = [d for d in os.listdir(accounts_dir) if os.path.isdir(os.path.join(accounts_dir, d)) and d.isdigit()]
    if len(dirs) == 0:
        raise Exception("未找到账户目录")
    if len(dirs) > 1:
        print(f"发现多个账户: {dirs}")
        # 使用最大数字的（最新账户）
        dirs.sort(key=lambda x: int(x), reverse=True)
    return dirs[0]

def generate_agent_id(account_id):
    """生成全局唯一 agentId"""
    acc_part = account_id[:8]
    ts = str(int(time.time() * 1000))[-7:]
    h1 = uuid.uuid4().hex[:6].upper()
    h2 = uuid.uuid4().hex[:4].upper()
    h3 = uuid.uuid4().hex[:6].upper()
    return f"MID-{acc_part}U{ts}-{h1}-{h2}-{h3}"

def main():
    account_id = get_account_id()
    print(f"账户ID: {account_id}")

    # 1. 下载
    tmp_dir = "/tmp/agent_install_ai_main_image"
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
    os.makedirs(tmp_dir, exist_ok=True)
    
    zip_path = os.path.join(tmp_dir, "agent.zip")
    print(f"正在下载 {ZIP_URL} ...")
    urllib.request.urlretrieve(ZIP_URL, zip_path)
    print(f"下载完成: {os.path.getsize(zip_path)} bytes")

    # 2. 解压（处理中文文件名）
    extract_dir = os.path.join(tmp_dir, "extracted")
    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zf:
        entries = [e for e in zf.namelist() if not e.endswith('/')]
        # 检测是否所有文件都在同一个顶层目录下
        top_parts = set(e.split('/')[0] for e in entries)
        prefix = ""
        if len(top_parts) == 1:
            prefix = list(top_parts)[0] + "/"
        for entry in entries:
            rel = entry[len(prefix):] if prefix else entry
            # 用 cp437 解码中文文件名（zip 标准编码）
            try:
                rel = rel.encode('cp437').decode('gbk')
            except:
                pass
            target = os.path.join(extract_dir, rel)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with zf.open(entry) as src, open(target, 'wb') as dst:
                dst.write(src.read())
    print(f"解压完成: {len(entries)} 个文件")

    # 3. 读取 profile（兼容 profile.jsonc 和 profile.template.jsonc）
    profile_path = os.path.join(extract_dir, "profile.jsonc")
    if not os.path.exists(profile_path):
        profile_path = os.path.join(extract_dir, "profile.template.jsonc")
    with open(profile_path, 'r') as f:
        raw = f.read()
    cleaned = re.sub(r'//.*$', '', raw, flags=re.MULTILINE)
    profile = json.loads(cleaned)
    print(f"智能体名称: {profile.get('name')}")
    # template 文件中 id/accountId 可能是注释掉的，确保字段存在
    profile.setdefault('id', '')
    profile.setdefault('accountId', '')
    profile.setdefault('createdAt', '')
    profile.setdefault('updatedAt', '')
    profile.setdefault('templateVersion', '1.0.0')

    # 4. 生成新ID
    new_id = generate_agent_id(account_id)
    agents_base = os.path.expanduser(f"~/.accio/accounts/{account_id}/agents")
    existing = set(os.listdir(agents_base)) if os.path.exists(agents_base) else set()
    while new_id in existing:
        new_id = generate_agent_id(account_id)
    print(f"新 ID: {new_id}")

    # 5. 修改 profile.jsonc
    profile['id'] = new_id
    profile['accountId'] = account_id
    profile['enabled'] = True
    
    # 重建 profile.jsonc（保留注释风格）
    default_model = {"provider": "auto", "name": "auto", "displayName": "专业"}
    model_val = profile.get('model', default_model)
    new_profile = f"""// Accio Agent 配置，可由 UI 或 API 修改

{{
  "id": "{profile['id']}",
  "accountId": "{profile['accountId']}",
  "name": "{profile.get('name', '')}",
  "avatar": {json.dumps(profile.get('avatar', 'avatar.png'))},
  "avatarUrl": {json.dumps(profile.get('avatarUrl', profile.get('avatar', 'avatar.png')))},
  "description": {json.dumps(profile.get('description', ''), ensure_ascii=False)},
  "vibe": "{profile.get('vibe', 'professional')}",
  "model": {json.dumps(model_val)},
  "runtime": "{profile.get('runtime', 'local')}",
  "toolInclude": {json.dumps(profile.get('toolInclude', []))},
  "creator": "{profile.get('creator', 'user')}",
  "agentType": "{profile.get('agentType', 'default')}",
  "pluginIds": {json.dumps(profile.get('pluginIds', []))},
  "createdAt": "{profile.get('createdAt', '')}",
  "updatedAt": "{profile.get('updatedAt', '')}",
  "templateVersion": "{profile.get('templateVersion', '1.0.0')}",
  "localMemoryIndex": {json.dumps(profile.get('localMemoryIndex', True))},
  "skillHarvestMode": "{profile.get('skillHarvestMode', 'manual')}",
  "enabled": true
}}
"""
    with open(profile_path, 'w') as f:
        f.write(new_profile)
    # 如果写的是 template 文件，同时生成标准 profile.jsonc
    if profile_path.endswith('.template.jsonc'):
        std_path = profile_path.replace('.template.jsonc', '.jsonc')
        with open(std_path, 'w') as f:
            f.write(new_profile)
        os.remove(profile_path)  # 删除旧模板

    # 6. 移动目录
    target_dir = os.path.join(agents_base, new_id)
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    shutil.move(extract_dir, target_dir)
    print(f"安装路径: {target_dir}")

    # 7. 替换 skills.jsonc 中的占位符
    skills_jsonc = os.path.join(target_dir, "agent-core", "skills", "skills.jsonc")
    if os.path.exists(skills_jsonc):
        skills_abs = os.path.join(target_dir, "agent-core", "skills")
        with open(skills_jsonc, 'r') as f:
            content = f.read()
        content = content.replace("<AGENT_SKILLS_DIR>", skills_abs)
        with open(skills_jsonc, 'w') as f:
            f.write(content)
        print(f"skills.jsonc 占位符已替换")

    # 8. 校验
    with open(os.path.join(target_dir, "profile.jsonc"), 'r') as f:
        raw_v = f.read()
    pv = json.loads(re.sub(r'//.*$', '', raw_v, flags=re.MULTILINE))
    
    # 统计技能
    skills_dir = os.path.join(target_dir, "agent-core", "skills")
    skill_count = 0
    if os.path.exists(skills_dir):
        skill_count = len([d for d in os.listdir(skills_dir) if os.path.isdir(os.path.join(skills_dir, d))])

    print("\n========== 安装完成 ==========")
    print(f"名称:       {pv.get('name')}")
    print(f"路径:       {target_dir}")
    print(f"ID:         {pv.get('id')}")
    print(f"Enabled:    {pv.get('enabled')}")
    print(f"技能数量:   {skill_count}")
    print("==============================")

if __name__ == "__main__":
    main()
