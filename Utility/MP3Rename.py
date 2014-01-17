from   Utility.Utility import *
import Utility.HomeUtility as Home
import Utility.Sql as sql

if Globals.UseMP3:
    import stagger

def dump_mp3_tags(tag):
    data = []
    data.append(['title', tag.title])
    data.append(['artist', tag.artist])
    data.append(['album_artist', tag.album_artist])
    data.append(['composer', tag.composer])
    data.append(['album', tag.album])
    data.append(['track', tag.track])
    data.append(['date', tag.date])
    PrettyPrint(data, 'mp3')
    #PrettyPrint(tag.items())
    #PrettyPrint(dir(tag))
    #Exit()

class MP3Rename():

    Columns = [
        ['idx'              , 'INTEGER primary key autoincrement'     ],
        ['path'             , 'text'    ],
        ['folder'           , 'text'    ],
        ['artist'           , 'text'    ],
        #['artist2'          , 'text'    ],
        ['album'            , 'text'    ],
        ['title'            , 'text'    ],
        ['new_path'         , 'text'    ],
        ['new_folder'       , 'text'    ],
        ['old_folder'       , 'text'    ],
    ]

    def __init__(self, Folder):
        self.Table = 'MP3Rename'
        self.errors = []
        self.UseExistingTable = False
        self.Verbose = False
        self.Folder = Folder

    def add_files(self, Debug=False):
        Trace(self.Folder)

        #loweredFolder = Folder.lower()
        data = []
        debugData = []
        count = 0
        for file in FindFiles(self.Folder):
            count += 1
            if not Debug:
                dbg_print(count)
            ext = os.path.splitext(file)[1]
            if 'Music' != Home.MediaTypeFromExtension(ext):
                #print('skipping', file)
                continue

            try:
                tag = stagger.read_tag(file)
            except:
                #print('failed', file)
                self.errors.append(file)
                continue
            if Debug:
                dump_mp3_tags(tag)

            artist = ''
            if not artist:
                artist = tag.album_artist
            if not artist:
                artist = tag.artist
            if not artist:
                artist = tag.composer
            artist = normalize_name(artist)

            folder = os.path.dirname(file)

            album = tag.album
            album = normalize_name(album)

            title = tag.title
            title = normalize_name(title)

            if album == '' or title == '':
                continue

            newPath = r'%s%s%s%s%s%s%s%s' % (self.Folder, os.sep, artist, os.sep, album, os.sep, title, ext)
            oldPath = file
            if Debug:
                if os.path.dirname(newPath).lower() != os.path.dirname(oldPath).lower():
                    debugData.append([newPath, oldPath])

            data.append([file, folder, artist, album, title, newPath, os.path.dirname(newPath), os.path.dirname(oldPath)])
            #if len(data) == 20:
            #    break

        print()

        #PrettyPrint(data)
        PrettyPrint(debugData)
        sql.write_to_table(self.Table, data, MP3Rename.Columns, UseExistingTable=self.UseExistingTable, SkipInsert=['idx'], Verbose=self.Verbose)
        Log('Inserted %d rows' % (len(data)))

    def fix_various_artists(self):

        folders = sql.execute('select distinct folder from %s' % (self.Table), Flatten=True)
        for folder in folders:
            albums = sql.execute('select distinct album from %s where folder=?' % (self.Table), Data=[folder], Flatten=True)
            for album in albums:
                rows = sql.execute('select distinct artist from %s where folder=? and album=?' % (self.Table), Data=[folder, album], Flatten=True)
                if len(rows) > 1:
                    artist = 'Various Artists'
                    for row in rows:
                        if 'various' not in row.lower():
                            artist = artist + os.sep + row
                            break

                    lowered = list(map(str.lower, rows))
                    lowered = [ re.sub(r'\W+', '', row) for row in lowered ]
                    lowered = list(set(lowered))

                    artist = ternary(len(lowered) > 1, artist, rows[0])
                    PrettyPrint(rows, 'Multiple artists for (%s)     (%s) %s' % (artist, album, folder))

                    rows = sql.execute('select idx,path,title from %s where folder=? and album=?' % (self.Table), Data=[folder, album])
                    for row in rows:
                        ext = os.path.splitext(row[1])[1]
                        title = row[2]
                        newPath = r'%s%s%s%s%s%s%s%s' % (self.Folder, os.sep, artist, os.sep, album, os.sep, title, ext)
                        sql.execute("update %s set new_path=? , new_folder=? where idx=?" % (self.Table), Data=[newPath, os.path.dirname(newPath), row[0]])

    def fix_album_names2(self):
        Trace()
        albums = sql.execute('select distinct album from %s' % (self.Table), Flatten=True)
        for idx, album in enumerate(albums):
            rows = sql.execute('select distinct old_folder from %s where album=?' % (self.Table), Data=[album], Flatten=True)
            if len(rows) > 1:
                PrettyPrint(rows, '(%s)' % (album))

                dst_folder = rows[0]
                move_rows = sql.execute('select idx,path,title from %s where album=? and folder <> ?' % (self.Table), Data=[album, dst_folder])
                for row in move_rows:
                    ext = os.path.splitext(row[1])[1]
                    title = row[2]
                    fileName = '%s%s' % (title, ext)
                    newPath = GenUniqueFileNamePlain(fileName, dst_folder, '')
                    #print(newPath)
                    sql.execute("update %s set new_path=? , new_folder=? where idx=?" % (self.Table), Data=[newPath, os.path.dirname(newPath), row[0]])


    def fix_album_names(self):
        Trace()
        artists = sql.execute('select distinct artist from %s' % (self.Table), Flatten=True)
        for idx, artist in enumerate(artists):
            rows = sql.execute('select distinct album from %s where artist=?' % (self.Table), Data=[artist], Flatten=True)
            if len(rows) > 1:

                lowered = list(map(str.lower, rows))
                lowered = [ re.sub(r'\W+', '', row) for row in lowered ]

                if len(list(set(lowered))) == len(rows):
                    continue

                values = list(range(len(lowered)))
                values.reverse()
                for index in values:
                    try:
                        found = lowered[0 : index].index(lowered[index])
                    except:
                        continue

                    src_album = rows[index]
                    dst_album = rows[found]
                    #print('Move (%s)    (%s)' % (src_album, dst_album))

                    dst_folders = sql.execute('select distinct old_folder from %s where artist=? and album=?' % (self.Table), Data=[artist, dst_album], Flatten=True)
                    if len(dst_folders) > 1:
                        Error('multiple dest folders', dst_folders)
                        Exit()

                    dst_folder = dst_folders[0]

                    move_rows = sql.execute('select idx,path,title from %s where artist=? and album=?' % (self.Table), Data=[artist, src_album])
                    for row in move_rows:
                        ext = os.path.splitext(row[1])[1]
                        title = row[2]
                        fileName = '%s%s' % (title, ext)
                        newPath = GenUniqueFileNamePlain(fileName, dst_folder, '')
                        #print(newPath)
                        sql.execute("update %s set new_path=? , new_folder=? where idx=?" % (self.Table), Data=[newPath, os.path.dirname(newPath), row[0]])

    def set_new_path(self, artist, album, where, where_data):
        rows = sql.execute('select idx,path,title from %s where %s' % (self.Table, where), Data=where_data)
        for row in rows:
            ext = os.path.splitext(row[1])[1]
            title = row[2]
            newPath = r'%s%s%s%s%s%s%s%s' % (self.Folder, os.sep, artist, os.sep, album, os.sep, title, ext)
            print(newPath)
            #sql.execute("update %s set new_path=? , new_folder=? where idx=?" % (self.Table), Data=[newPath, os.path.dirname(newPath), row[0]])

    def move_to_new_paths(self):
        rows = sql.execute('select path,new_path from %s where new_folder != old_folder' % (self.Table))
        for idx, row in enumerate(rows):
            #print(row)
            orig_path = row[0]
            dest_path = row[1]
            dest_path = GenUniqueFileNamePlain(dest_path, os.path.dirname(dest_path), '')
            #if idx == 100:
            #    Exit()


            try:
                os.chmod(orig_path, stat.S_IRWXU)
                shutil.move(orig_path, dest_path)
                print('Moved to ', dest_path)
            except:
                ReportException()
                pass

    def dump(self):
        Trace()
        rows = sql.execute('select new_path from %s' % (self.Table), Flatten=True)
        for idx, row in enumerate(rows):
            dest_path = row
            dest_path = GenUniqueFileNamePlain(dest_path, os.path.dirname(dest_path), '')
            LogPlain(dest_path)

def normalize_name(value):
    special = r'\/`~@#$%^&*+={}|:;"\'<>?'
    for ch in special:
        value = value.replace(ch, ' ')
    value = value.replace('  ', ' ')
    value = value.replace('  ', ' ')
    value = value.replace('  ', ' ')
    return value
