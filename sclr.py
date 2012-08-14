import ConfigParser
import argparse
import os, os.path
import subprocess

SVN_LOG_CMD = r'svn log "%(REPO_BASE_URL)s/%(PATH)s/%(ITEM)s" %(SVN_USERNAME_PARAM)s -v -r%(START_DATE)s:%(END_DATE)s > "%(LOGNAME)s"'

class SCLRParser(object):
 
    OPTION_COMMANDS = ['logalias','logsuffix','*']
    REQUIRED_SETTINGS = ['startdate','enddate','repobaseurl']
    SETTINGS_SECTION_NAME = 'settings'

    parser = None
    config_file = None
    output_dir = None
    default_log_suffix = None

    start_date = None
    end_date = None
    repo_base_url = None
    svn_username = None
    svn_username_param = ''

    svn_log_commands = []

    def __init__(self, configfile, output_dir, default_log_suffix):
        self.config_file = configfile
        self.output_dir = output_dir
        self.default_log_suffix = default_log_suffix
        self.cp = self.build_parser()
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)

    def build_parser(self):
        cp = ConfigParser.SafeConfigParser(allow_no_value=True)
        cp.optionxform = str
        cp.read(self.config_file)
        return cp

    def get_logs(self):
        self.parse()
        for c in self.svn_log_commands:
            print c
            subprocess.call(c, shell=True)

    def parse(self):
        self.parse_settings()
        for s in self.cp.sections():
            if s == self.SETTINGS_SECTION_NAME:   # skip the settings section for actual commit log processing
                continue
            else:
                self.parse_section(s)

    def parse_settings(self):
        # check for required settings that are missing
        missing = [rs for rs in self.REQUIRED_SETTINGS if rs not in [s for s in self.cp.options(self.SETTINGS_SECTION_NAME)]]
        if missing:
            for m in missing:
                raise ConfigParser.ParsingError('Missing required option in [settings]: %s' % m)
        # get settings values
        for setting,value in self.cp.items(self.SETTINGS_SECTION_NAME):
            if setting == 'startdate':
                self.start_date = "{%s}" % value
            elif setting == 'enddate':
                self.end_date = "{%s}" % value
                if value.lower() == 'head':
                    self.end_date = 'HEAD'
            elif setting == 'repobaseurl':
                self.repo_base_url = value            
            elif setting == 'svnusername':
                self.svn_username = value
            else:
                print '! Unrecognized option in [settings]: %s; ignoring...' % setting

        # if we're using a SVN username, set up svn_username_param
        if self.svn_username:
            self.svn_username_param = '--username %s' % self.svn_username

    def parse_section(self, section_name):
        PATH = section_name
        # clean up the path specified in the section header so that it'll play nice with the svn_cmd format string
        if PATH.startswith('/'):
            PATH = PATH[1:]
        if PATH.endswith('/'):
            PATH = PATH[:-1]
        
        logalias = None
        try:
            logalias = self.cp.get(section_name, 'logalias')
        except(ConfigParser.NoOptionError):
            pass

        getall = False
        if self.cp.has_option(section_name, '*'):
            getall = True
        if getall and not logalias:
            raise ConfigParser.ParsingError("The '*' option cannot be specified without a 'logalias' option in the same section (%s)" % section_name)

        logsuffix = None
        try:
            logsuffix = self.cp.get(section_name, 'logsuffix')
            if getall:
                raise ConfigParser.ParsingError("The 'logsuffix' option cannot be specified with the '*' option in the same section; use the 'logalias' option instead (%s)" % section_name)
        except(ConfigParser.NoOptionError):
            pass

        # set up local vars to match the param names in the svn cmd so we can str format using "locals()"
        REPO_BASE_URL = self.repo_base_url
        SVN_USERNAME_PARAM = self.svn_username_param
        START_DATE = self.start_date
        END_DATE = self.end_date

        if getall:
            ITEM = ''
            LOGNAME = os.path.join(self.output_dir, logalias)
            self.svn_log_commands.append(SVN_LOG_CMD % locals())
        else:
            files = [f for f in self.cp.options(section_name) if f not in self.OPTION_COMMANDS]
            if len(files) == 0:
                print '! No files specified for section; did you forget "*"? (%s)' % section_name
            for f in files:
                ITEM = f
                _logsuffix = self.default_log_suffix if logsuffix is None else logsuffix
                LOGNAME = os.path.join(self.output_dir, logalias if logalias is not None else "%s%s" % (f,_logsuffix))
                self.svn_log_commands.append(SVN_LOG_CMD % locals())

def parse_args():
    parser = argparse.ArgumentParser(description='Retrieve SVN commit logs for specific files and dates.')
    parser.add_argument('--config_file', type=str, help='the .ini-formatted config file (default: %(default)s)', default='sclr.ini')
    parser.add_argument('--log_suffix', type=str, help='the log suffix to use when not specified for a section via the logsuffix or logalias options (default: %(default)s)', default='.log')
    parser.add_argument('--output_dir', type=str, help='the directory where commit logs should be written (default: %(default)s)', default='logs')
    return parser.parse_args()

if __name__=='__main__':
    args = parse_args()
    c = SCLRParser(args.config_file, args.output_dir, args.log_suffix)
    c.get_logs()