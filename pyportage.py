import subprocess
import re
import os
import struct

class XPAK():
    def __getitem__(self, index):
        self.f.seek(-self.data_len-16 + self.index[index][0],2)
        return self.f.read(self.index[index][1])
    def __init__(self, filename):
        self.f = open(filename)
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
    m = re.match('(>=|<=|>|<|)([^/]*)/([a-z-]*)([^:-]*)(-[^:]*)?(:.*)?', d)
    ret['cat'] = m.groups()[1]
    ret['pn'] = m.groups()[2]
    if ret['pn'].endswith('-'): ret['pn'] = ret['pn'][:-1]
    ret['pv'] = m.groups()[3]
    if not ret['pv']: ret['pv'] = '0'
    ret['slot'] = m.groups()[5]
    return ret

def ebuild_digest(ebuild):
    devnull = open('/dev/null', 'w')
    subprocess.Popen(['ebuild',ebuild,'digest'], stdout=devnull, stderr=devnull).communicate()

def emerge(args):
    fcat = open('/usr/portage/profiles/categories','w')
    fcat.write('sys-apps\n')
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
                    s = splitebuildname(d)
                    ebuild = '/usr/portage/%(cat)s/%(pn)s/%(pn)s-%(pv)s.ebuild' % s
                    if d[:2] == '>=':
                        pass
                    if s['slot']:
                        ebuild_data = 'SLOT="%s"' % s['slot'][1:]
                    else:
                        ebuild_data = 'SLOT="0"'
                    os.makedirs('/usr/portage/%(cat)s/%(pn)s' % s)
                    f = open(ebuild, 'w').write(ebuild_data)
                    ebuild_digest(ebuild)
        else:
            return [stdout, stderr]

if __name__ == "__main__":
    x = XPAK(sys.argv[1]+'.tbz2')
    os.makedirs('/usr/portage/sys-apps/portage')
    ebuild = '/usr/portage/sys-apps/portage/'+sys.argv[1]+'.ebuild'
    f = open(ebuild, 'w')
    f.write('''RDEPEND="%s"
SLOT="%s"
EAPI="%s"''' % (x['RDEPEND'][:-1], x['SLOT'][:-1], x['EAPI'][:-1]))
    f.close()
    ebuild_digest(ebuild)

    for line in emerge(['-op', 'sys-apps/portage'])[1].splitlines():
        if line.startswith('[ebuild'): print splitebuildname(re.split('\[ebuild.*\] ', line)[1][:-1])['pn']

