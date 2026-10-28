"""Invite-only online identities. Independent users, hashed passwords and revocable sessions."""
from __future__ import annotations
import argparse,hashlib,hmac,json,re,secrets,time
from fastapi import HTTPException
from gmf_v3.contracts import uid

class Identity:
 def __init__(self,store,clock=time.time):self.store=store;self.clock=clock
 def digest(self,value):return hashlib.sha256(value.encode()).hexdigest()
 def email(self,value):
  if not isinstance(value,str) or not re.fullmatch(r'[^\s@]{1,120}@[^\s@]{1,120}\.[^\s@]{1,50}',value):raise ValueError('请输入有效邮箱')
  return value.casefold()
 def password(self,value,salt=None):
  if not isinstance(value,str) or not 12<=len(value)<=256:raise ValueError('密码需要 12–256 个字符')
  salt=salt or secrets.token_hex(16)
  hashed=hashlib.scrypt(value.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1,maxmem=64*1024*1024).hex()
  return salt+':'+hashed
 def invite(self,email,role='student'):
  email=self.email(email)
  if role not in ('admin','student'):raise ValueError('Invalid role')
  value=secrets.token_urlsafe(32)
  with self.store.connect(write=True) as c:c.execute('INSERT INTO v43_invites VALUES(?,?,?,?,0)',(self.digest(value),email,role,int(self.clock())+86400))
  return value
 def register(self,email,password,invite):
  email=self.email(email);password_hash=self.password(password)
  if not isinstance(invite,str):raise ValueError('邀请无效或已过期')
  with self.store.connect(write=True) as c:
   row=c.execute('SELECT * FROM v43_invites WHERE invite_hash=?',(self.digest(invite),)).fetchone()
   if not row or row['used'] or row['expires_at']<self.clock() or row['email']!=email:raise ValueError('邀请无效或已过期')
   if c.execute('SELECT 1 FROM v43_users WHERE email=?',(email,)).fetchone():raise ValueError('该邮箱已注册，请登录')
   user=uid('user');c.execute('INSERT INTO v43_users VALUES(?,?,?,?,?,0)',(user,email,password_hash,row['role'],int(self.clock())))
   c.execute('UPDATE v43_invites SET used=1 WHERE invite_hash=?',(self.digest(invite),))
  return user
 def login(self,email,password,client='unknown'):
  email=self.email(email);at=int(self.clock());bucket=self.digest(email+'|'+client)
  with self.store.connect(write=True) as c:
   limit=c.execute('SELECT * FROM v43_login_limits WHERE bucket=?',(bucket,)).fetchone()
   if limit and limit['reset_at']>at and limit['attempts']>=5:raise HTTPException(429,'登录尝试过多，请 15 分钟后重试')
   c.execute('INSERT INTO v43_login_limits VALUES(?,1,?) ON CONFLICT(bucket) DO UPDATE SET attempts=CASE WHEN reset_at<=? THEN 1 ELSE attempts+1 END,reset_at=CASE WHEN reset_at<=? THEN ? ELSE reset_at END',(bucket,at+900,at,at,at+900))
   row=c.execute('SELECT * FROM v43_users WHERE email=?',(email,)).fetchone()
  # Constant-cost work for unknown accounts; do not disclose account existence.
  salt=row['password_hash'].split(':')[0] if row else '00'*16
  try:match=self.password(password,salt)
  except ValueError:match=self.password('invalid-password',salt)
  if not row or row['disabled'] or not hmac.compare_digest(match,row['password_hash']):raise HTTPException(401,{'code':'auth_required','message':'邮箱或密码不正确'})
  token=secrets.token_urlsafe(32)
  with self.store.connect(write=True) as c:
   c.execute('DELETE FROM v43_login_limits WHERE bucket=?',(bucket,));c.execute('DELETE FROM v43_logins WHERE expires_at<=?',(at,))
   c.execute('INSERT INTO v43_logins VALUES(?,?,?)',(self.digest(token),row['user_id'],at+14*86400))
  return token
 def principal(self,token):
  if not token:return None
  with self.store.connect() as c:
   row=c.execute('SELECT u.user_id,u.role,u.email FROM v43_logins s JOIN v43_users u ON u.user_id=s.user_id WHERE s.token_hash=? AND s.expires_at>? AND u.disabled=0',(self.digest(token),int(self.clock()))).fetchone()
  return {'owner_id':row['user_id'],'role':row['role'],'email':row['email']} if row else None
 def logout(self,token):
  with self.store.connect(write=True) as c:c.execute('DELETE FROM v43_logins WHERE token_hash=?',(self.digest(token),))

def main():
 parser=argparse.ArgumentParser(description='Issue a one-use invitation on the private backend host')
 parser.add_argument('invite',choices=['invite']);parser.add_argument('--email',required=True);parser.add_argument('--role',choices=['admin','student'],default='student');args=parser.parse_args()
 import os
 from .bank import Bank
 bank=Bank(os.environ['GMF_DATA_DIR']);token=Identity(bank.store).invite(args.email,args.role)
 # Only an explicit operator CLI prints the new invitation; never server or access logs.
 print(os.environ['GMF_PUBLIC_ORIGIN'].rstrip('/')+'/assessment/login.html#invite='+token)
if __name__=='__main__':main()
