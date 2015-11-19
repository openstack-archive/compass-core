import os
import yaml
import sys
from Cheetah.Template import Template

def init(file):
    with open(file) as fd:
        return yaml.load(fd)

def decorator(func):
    def wrapter(s, seq):
        host_list = s.get('hosts', [])
        result = []
        for host in host_list:
            s = func(s, seq, host)
            if not s:
               continue
            result.append(s)
        if len(result) == 0:
            return ""
        else:
            return "\"" + seq.join(result) + "\""
    return wrapter

@decorator
def hostnames(s, seq, host=None):
    return host.get('name', '')

@decorator
def hostroles(s, seq, host=None):
    return "%s=%s" % (host.get('name', ''), ','.join(host.get('roles', [])))

@decorator
def hostmacs(s, seq, host=None):
    return host.get('mac', '')

def export_config_file(s, conf_dir, ofile):
    env = {}
    env.update(s)
    if env.get('hosts', []):
        env.pop('hosts')

    env.update({'NEUTRON': os.path.join(conf_dir, "neutron_cfg.yaml")})
    env.update({'NETWORK': os.path.join(conf_dir, "network_cfg.yaml")})

    env.update({'TYPE': s.get('TYPE', "virtual")})
    env.update({'FLAVOR': s.get('FLAVOR', "cluster")})
    env.update({'HOSTNAMES': hostnames(s, ',')})
    env.update({'HOST_ROLES': hostroles(s, ';')})

    value = hostmacs(s, ',')
    if len(value) > 0:
        env.update({'HOST_MACS': value})

    os.system("echo \#config file deployment parameter > %s" % ofile)
    for k, v in env.items():
        os.system("echo 'export %s=${%s:-%s}' >> %s" % (k, k, v, ofile))

def export_reset_file(s, tmpl_dir, output_dir, output_file):
    tmpl_file_name = s.get('POWER_TOOL', '')
    if not tmpl_file_name:
        return

    tmpl = Template(file=os.path.join(tmpl_dir,'power', tmpl_file_name + '.tmpl'), searchList=s)

    reset_file_name = os.path.join(output_dir, tmpl_file_name + '.sh')
    with open(reset_file_name, 'w') as f:
        f.write(tmpl.respond())

    os.system("echo 'export POWER_MANAGE=%s' >> %s" % (reset_file_name, output_file))

if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("parameter wrong%d %s" % (len(sys.argv), sys.argv))
        sys.exit(1)

    _, config_file, conf_dir, tmpl_dir, output_dir, output_file = sys.argv

    if not os.path.exists(config_file):
        print("%s is not exist" % config_file)
        sys.exit(1)

    data = init(config_file)

    export_config_file(data, conf_dir, os.path.join(output_dir, output_file))
    export_reset_file(data, tmpl_dir, output_dir, os.path.join(output_dir, output_file))

    sys.exit(0)

