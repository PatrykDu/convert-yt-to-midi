from mido import MidiFile

def describe(path):
    mid = MidiFile(path)
    print(f"\n=== {path} ===")
    print(f"Type: {mid.type}, Tracks: {len(mid.tracks)}, Ticks/beat: {mid.ticks_per_beat}")
    for i, tr in enumerate(mid.tracks):
        metas = [msg for msg in tr if msg.is_meta]
        notes = sum(1 for msg in tr if msg.type in ('note_on','note_off'))
        print(f"\n Track {i}:")
        print(f"   Meta-messages ({len(metas)}):")
        for msg in metas:
            print(f"     {msg}")
        print(f"   Note events: {notes}")

if __name__ == '__main__':
    # Podmień nazwy plików na swoje
    file1 = 'Cook Da Books - Your eyes PLUS OCTANE.mid'
    file2 = 'out.mid'
    describe(file1)
    describe(file2)