import subprocess
import re
import os
import struct
import sys
import glob
import shutil

class XPAK():
    def __getitem__(self, index):
        self.f.seek(-self.data_len-16 + self.index[index][0],2)
        return self.f.read(self.index[index][1])
    def __init__(self, f):
        self.f = f
        self.f.seek(-4, 2)
        if self.f.read(4) != 'STOP':
            print 'oops'
        self.f.seek(-8,2)
        xpak_offset = struct.unpack('>I',self.f.read(4))[0]
        self.f.seek(-xpak_offset - 8,2)
        if self.f.read(8) != 'XPAKPACK':
            print 'oops'
        self.index_len = struct.unpack('>I',self.f.read(4))[0]
        self.data_len = struct.unpack('>I',self.f.read(4))[0]

        index_i = 0
        self.index = {}
        while index_i < self.index_len:
            pathname_len = struct.unpack('>I',self.f.read(4))[0]
            pathname = self.f.read(pathname_len)
            self.index[pathname] = (struct.unpack('>I',self.f.read(4))[0],
             struct.unpack('>I',self.f.read(4))[0])
        
            index_i += pathname_len+12

def splitebuildname(d):
    ret = {}
    if d.startswith('>=') or d.startswith('<='):
        ret['operator'] = d[:2]
        d = d[2:]
    if d.startswith('>') or d.startswith('<') or d.startswith('~'):
        ret['operator'] = d[0]
        d = d[1:]
    if '/' in d:
        s = d.split('/')
        ret['cat'] = s[0]
        d = s[1]
    if ':' in d:
        s = d.split(':')
        ret['slot'] = s[1]
        d = s[0]
    else:
        ret['slot'] = '0'
    m = re.match('(.*)-([0-9].*)', d)
    if m:
        ret['pn'] = m.groups()[0]
        ret['pv'] = m.groups()[1]
    else:
        ret['pn'] = d
        ret['pv'] = 0
    return ret

def ebuild_digest(ebuild):
    devnull = open('/dev/null', 'w')
    subprocess.Popen(['ebuild',ebuild,'digest'], stdout=devnull, stderr=devnull).communicate()

def dummyebuild(d):
    s = splitebuildname(d)
    ebuild = '/usr/portage/%(cat)s/%(pn)s/%(pn)s-%(pv)s.ebuild' % s
    ebuild_data = 'SLOT="%s"' % s['slot']
    os.makedirs('/usr/portage/%(cat)s/%(pn)s' % s)
    f = open(ebuild, 'w').write(ebuild_data)
    ebuild_digest(ebuild)

def emerge(args):
    fcat = open('/usr/portage/profiles/categories','w')
    fcat.write('what-ever\n')
    fcat.flush()
    while 1:
        p = subprocess.Popen(['emerge']+args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        if 'has a category that is not listed' in stderr:
            for line in stderr.splitlines():
                if 'has a category that is not listed' in line:
                    fcat.write("%s\n" % line.split("'")[1].split('/')[0])
                    fcat.flush()
        elif 'emerge: there are no ebuilds to satisfy' in stdout:
            for line in stdout.splitlines():
                if line.startswith('emerge: there are no ebuilds to satisfy "'):
                    d = line.split('"')[1]
                    dummyebuild(d)
        elif 'or don\'t exist:' in stderr:
            found = False
            for line in stderr.splitlines():
                if found:
                    ds = line.split(' ')
                    for d in ds: dummyebuild(d)
                    break
                if line.startswith('!!! masked or don\'t exist:'): found = True
        else:
            return [stdout, stderr]

if __name__ == "__main__":
    if sys.argv[1] == 'splitebuildname':
        print splitebuildname(sys.argv[2])
    elif sys.argv[1] == 'emerge':
        stdin, stderr = emerge(sys.argv[2:])
        print stdin, stderr
    elif sys.argv[1] == 'RDEPEND':
        p = sys.argv[3]
        ftbz2 = open(p+'.tbz2')
        pn = sys.argv[2]
        x =           XPAK(ftbz2)
        for dir in glob.glob('/usr/portage/*-*')+glob.glob('/usr/portage/virtual*'): shutil.rmtree(dir)
        try:
            os.remove('/usr/portage/profiles/categories')
        except:
            pass
        os.makedirs('/usr/portage/what-ever/'+pn)
        ebuild = '/usr/portage/what-ever/'+pn+'/'+p+'.ebuild'
        febuild = open(ebuild, 'w')
        if 'RDEPEND' in x.index: RDEPEND = x['RDEPEND'][:-1]
        else: RDEPEND = ''
        febuild.write('''RDEPEND="%s"
SLOT="%s"
EAPI="%s"''' % (RDEPEND, x['SLOT'][:-1], x['EAPI'][:-1]))
        febuild.close()
        ebuild_digest(ebuild)
        for line in         emerge(['-op', 'what-ever/'+pn])[1].splitlines():
            if line.startswith('[ebuild'):
                 print                 splitebuildname(re.split('\[ebuild.*\] ', line)[1][:-1])['pn']

        for dir in glob.glob('/usr/portage/*-*')+glob.glob('/usr/portage/virtual'): shutil.rmtree(dir)
        try:
            os.remove('/usr/portage/profiles/categories')
        except:
            pass
