import json
import os
import sqlite3
import csv
from sqlite3.dbapi2 import Cursor
from typing import Iterable, List, Mapping, NamedTuple, Optional, Tuple

import numpy as np
from rdkit.DataStructs.cDataStructs import BitVectToText, CreateFromBitString, ExplicitBitVect

from .util import fingerprint_from_smiles, Consts, atomic_units2eV
from .orbital_calculations import MolecularOrbital, SerializedMolecularOrbital

# for idx, row in enumerate(blyp_data):
#     if row[0] == pm7_data[idx][0]:
#         blyp_data[idx] = tuple(row[0] + pm7_data[idx][1] + row[1])
#     else:
#         print(f"line {idx} , molNames not the same, blyp name = {row[0]} pm7 name = {pm7_data[idx][0]}")

class DatasetItem(NamedTuple):
    mol_id: str
    E_pm7: float
    E_blyp: float
    smiles: str
    fingerprint: ExplicitBitVect
    serialized_molecular_orbital: Optional[str]

class DB:

    BLYP = 'E_blyp'
    PM7 = 'E_pm7'

    COMPUTED_PAIRS_TABLE_NAME = "computed_pairs_{table_id}"

    def __init__(self, database_path: str):
        self.conn = sqlite3.connect(database_path, detect_types=sqlite3.PARSE_DECLTYPES)
        self.cur = self.conn.cursor()
        self.register_adapters()
        self.register_converters()

    def table_exists(self):
        r = self.cur.execute("SELECT name FROM sqlite_master WHERE type=`table` AND name=`dataset`")
        if len(r.fetchall()) == 1:
            return True
        else:
            return False

    def create_dataset_table(self):
        """
        mol_id is the ZINC id eg: `ZINC000000038842`
        E_pm7, E_blyp are energies from each calculation eg -0.31885
        smiles is the smiles repr for that molecule
        rdk_fingerprint is the bitvector for the fingerprint generated by RDKFingerprint
        serialized_molecular_orbital is a .orbital_calculations.SerializedMolecularOrbital serialized with json.
        """


        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS dataset (
            mol_id text, E_pm7 real, E_blyp real, smiles text, rdk_fingerprint explicitbitvect, serialized_molecular_orbital type_serialized_molecular_orbital
        )
        """)

    ###################################
    ### Adapter and converter functions
    ###################################

    def register_adapters(self):
        "Register adapters for custom types in our tables"
        sqlite3.register_adapter(ExplicitBitVect, self.adapt_fingerprint)
        sqlite3.register_adapter(SerializedMolecularOrbital, self.adapt_serialized_molecular_orbital)
    def register_converters(self):
        "Register converters for custom types in our tables"
        sqlite3.register_converter('explicitbitvect', self.convert_fingerprint)
        sqlite3.register_converter('type_serialized_molecular_orbital', self.convert_serialized_molecular_orbital)


    ### Fingerprints
    def adapt_fingerprint(self, fp: ExplicitBitVect) -> str:
        b = fp.ToBitString().encode("utf-8")
        return b

    def convert_fingerprint(self, fp_str) -> ExplicitBitVect:
        return CreateFromBitString(fp_str)

    ### Serialized Molecular Orbitals
    def adapt_serialized_molecular_orbital(self, serialized_molecular_orbital: SerializedMolecularOrbital) -> str:
        return json.dumps(serialized_molecular_orbital)

    def convert_serialized_molecular_orbital(self, serialized_mo: bytes) -> SerializedMolecularOrbital:
        return json.loads(serialized_mo)


    ######################
    ### Writing operations
    ######################

    def add_dataset(self, dataset: Iterable[DatasetItem]):
        for mol_id, pm7, blyp, smiles, fingerprint_bitvect, serialized_molecular_orbital in dataset:
            self.add_dataset_row(DatasetItem(mol_id, pm7, blyp, smiles, fingerprint_bitvect, serialized_molecular_orbital))
        self.commit()
        
    def add_dataset_row(self, row: DatasetItem):
        mol_id, pm7, blyp, smiles, fingerprint_bitvect, serialized_molecular_orbital = row
        self.cur.execute(
                "INSERT INTO dataset VALUES (?,?,?,?,?,?)", (mol_id, float(pm7), float(blyp), smiles, fingerprint_bitvect, serialized_molecular_orbital)
            )

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.commit()
        self.conn.close()

    ######################
    ### Reading Operations
    ######################

    def get_all(self):
        r = self.get_all_cursor()
        return r.fetchall()

    def get_all_cursor(self) -> Cursor:
        r = self.cur.execute(
            "SELECT * FROM dataset ORDER BY `rowid`"
        )
        return r

    def get_row_from_mol_id(self, mol_id):
        r = self.cur.execute(
            f"SELECT * FROM dataset WHERE mol_id='{mol_id}'"
        )
        fetch = r.fetchall()
        if fetch.__len__() > 1:
            print(f"WARNING: fetching row for  mol_id {mol_id} gave more than one row result")
        return fetch[0]

    def get_dE_from_mol_id(self, mol_id):
        row = self.get_row_from_mol_id(mol_id)
        pm7, blyp = row[1:3]
        dE = blyp - pm7
        return dE

    def base_get_energies(self, energy: str) -> List[float]:
        "energy: str = self.PM7 or self.BLYP"
        col = "E_pm7" if energy == self.PM7 else "E_blyp"
        r = self.cur.execute(
            f"SELECT {col} FROM dataset ORDER BY `rowid`"
        )
        ### Reshape [(val,), (val2,)...] into [val, val2,...]
        return np.asarray(r.fetchall())[:,0]

    def get_blyp_energies(self) -> List[float]:
        "Return BLYP energies sorted by rowid"
        return self.base_get_energies(self.BLYP)

    def get_pm7_energies(self) -> List[float]:
        "Return PM7 energies sorted by rowid"
        return self.base_get_energies(self.PM7)

    def get_pm7_energies_with_smiles(self):
        r = self.cur.execute(
            f"SELECT `{self.PM7}`, `smiles` FROM dataset ORDER BY `rowid`"
        )
        return r.fetchall()

    def get_mol_ids(self) -> List[str]:
        "Return mol_ids ordered by rowid"
        r = self.cur.execute(
            "SELECT mol_id FROM dataset ORDER BY `rowid`"
        )
        return [x[0] for x in r.fetchall()]

    def get_smiles(self) -> np.ndarray:
        "Return smiles ordered by rowid"
        r = self.cur.execute(
            "SELECT `smiles` FROM dataset ORDER BY `rowid`"
        )
        return np.array(r.fetchall())[:,0]

    def get_smiles_for_mol(self, mol_id):
        r = self.cur.execute(
            f"SELECT `smiles` WHERE `mol_id`={mol_id}"
        )
        return r.fetchone()

    def get_fingerprints(self):
        r = self.cur.execute(
            "SELECT `rdk_fingerprint` FROM dataset ORDER BY `rowid`"
        )
        return [x[0] for x in r.fetchall()]

    def get_molecular_orbitals(self) -> List[SerializedMolecularOrbital]:
        r = self.cur.execute(
            "SELECT `serialized_molecular_orbital` FROM dataset ORDER BY `rowid`"
        )
        return [x[0] for x in r.fetchall()] 

def main(database_path, orbitalsDir, BLYP_energies_file, PM7_energies_file, SMILES_file):
    """
    Example parameters:
    database_path = "y4_python\\1k_molecule_database_eV.db"
    orbitalsDir = "sampleInputs\\11k_orbitals"
    BLYP_energies_file = "sampleInputs\\11k_BLYP_homo_energies.csv"
    PM7_energies_file = "sampleInputs\\11k_PM7_homo_energies.csv"
    SMILES_file = "sampleInputs\\SMILES_labels.csv"
    """
    print(database_path, orbitalsDir, BLYP_energies_file, PM7_energies_file, SMILES_file)

    ### Read the smiles representations of each molecule into a dictionary.
    ### This gives us O(1) lookup time, and ~1000 entries shouldn't be too memory demanding. (TODO: what about 100,000? :O )
    SMILES_dict: Mapping[str,str] = {}
    with open(SMILES_file, 'r') as F:

        reader = csv.reader(F)
        ### Each row is (smiles, molName)
        for row in reader:
            SMILES_dict[row[1].strip()] = row[0].strip()


    db = DB(database_path)

    db.create_dataset_table()


    with open(BLYP_energies_file, 'r', newline='') as BLYP_File, open(PM7_energies_file, 'r', newline='') as PM7_File:
        ### data is [[molName, E_blyp], ...]
        blyp_reader = csv.reader(BLYP_File)
        pm7_reader = csv.reader(PM7_File)
        ### TODO: New loop, which uses all the generators
        for idx, blyp_row in enumerate(blyp_reader):
            blyp_mol_id, E_blyp = [x.strip() for x in blyp_row]
            pm7_mol_id, E_pm7 = pm7_row = [x.strip() for x in next(pm7_reader)]
            if blyp_mol_id != pm7_mol_id:
                raise Exception(f"blyp_mol_id != pm7_mol_id. blyp_mol_id = {blyp_mol_id}, pm7_mol_id={pm7_mol_id}")
            smiles = SMILES_dict[blyp_mol_id]
            rdk_fingerprint = fingerprint_from_smiles(smiles, Consts.RDK_FP)
            if not isinstance(rdk_fingerprint, ExplicitBitVect):
                raise Exception("rdk_fingerprint was not instance of ExplicitBitVect")
            try:
                serialized_molecular_orbital = MolecularOrbital.fromJsonFile(
                    os.path.join(orbitalsDir, f"{blyp_mol_id}.json")
                    , mo_number=MolecularOrbital.HOMO
                ).serialize()
            except FileNotFoundError as e:
                print(e)
                print("Molecular orbital file not found. For this molecule will insert null in serialized_mol_orb column")
                serialized_molecular_orbital = None


            db.add_dataset_row(
                DatasetItem(blyp_mol_id, atomic_units2eV(float(E_pm7)), atomic_units2eV(float(E_blyp)), smiles, rdk_fingerprint, serialized_molecular_orbital)
            )
            print(idx)
        db.commit()
        db.close()



if __name__ == "__main__":
    import sys
    ### Pass the database and input files as arguments
    # database_path, orbitalsDir, BLYP_energies_file, PM7_energies_file, SMILES_file = sys.argv[1:]
    main(*sys.argv[1:])