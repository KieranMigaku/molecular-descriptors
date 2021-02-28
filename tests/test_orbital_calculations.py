from typing import List
import unittest

import numpy as np

from y4_python.python_modules.orbital_calculations import MolecularOrbital, PointMass as PM, calc_inertia_tensor, calc_principle_axes, calc_center_of_mass


class TestOrbitalCalculations(unittest.TestCase):

    def test_calc_inertia_tensor(self):
        """
        Compare the calculated inertia tensor with some standard ones.
        """
        ### no points in each side ( = length of side + 1)
        a = 11
        sideLength = a-1

        ### total points = a^2
        N = (a+1)**2

        ### total mass
        m = 0.25

        # masses: List[PM] = []
        # for x in range(a):
        #     for y in range(a):
        #         masses.append(PM(mass=m/N, coords=(x/(a-1), y/(a-1), 0)))

        masses = [
            PM(mass=0.25, coords=np.array((0,0,0)))
            , PM(mass=0.25, coords=np.array((0,1,0)))
            , PM(mass=0.25, coords=np.array((1,0,0)))
            , PM(mass=0.25, coords=np.array((1,1,0)))
        ]

        xx = yy = m*(2)
        zz = 2*xx
        xy = yx = -m*((1)**2)

        ### inertia tensor of square
        expected: np.ndarray = np.array([
            [xx, xy, 0]
            , [yx, yy, 0]
            , [0, 0, zz]
        ])

        result = calc_inertia_tensor(masses)

        print("masses:")
        print(masses)
        print(f"length of masses = {len(masses)}")
        print("\n\nexpected:")
        print(expected)
        print("\n\nresult:")
        print(result)

        exp_principle_axes = calc_principle_axes(expected)
        res_principle_axes = calc_principle_axes(result)

        print("\n\nexpected_principle_axes:")
        print(exp_principle_axes)
        print("\n\n result_principle_axes:")
        print(res_principle_axes)
        #self.assertEqual(exp_principle_axes.all(), res_principle_axes.all())

        for idx, row in enumerate(expected):
            self.assertEqual(row.all(), result[idx].all())

        ### inertia tensor of triangle

    def test_calc_center_of_mass(self):
        masses = [
            PM(mass=1, coords=np.array((0,0,0)))
            , PM(mass=1, coords=np.array((-1,0,0)))
            , PM(mass=1, coords=np.array((1,0,0)))
        ]
        expected = np.array([0,0,0])
        result = calc_center_of_mass(masses)

        self.assertEqual(expected.all(), result.all())

    def test_homo_lumo_numbers_from_json(self):
        from y4_python.python_modules.orbital_calculations import MolecularOrbital

        test = {
            "1": {"occupied": True},
            "2": {"occupied": False}
        }

        exp_homoNum, exp_lumoNum = 1,2

        homoNum, lumoNum = MolecularOrbital.homoLumoNumbersFromJson(test)

        self.assertEqual(homoNum, exp_homoNum)
        self.assertEqual(lumoNum, exp_lumoNum)

        test = {
            "24": {"occupied": True},
            "atomic_coords": [1,2,3],
            "56": {"occupied": False}
        }

        exp_homoNum, exp_lumoNum = 24,56

        homoNum, lumoNum = MolecularOrbital.homoLumoNumbersFromJson(test)

        self.assertEqual(homoNum, exp_homoNum)
        self.assertEqual(lumoNum, exp_lumoNum)

        test = {
            "56": {"occupied": False},
            "atomic_coords": [1,2,3],
            "55": {"occupied": True}
        }

        exp_homoNum, exp_lumoNum = 55,56

        homoNum, lumoNum = MolecularOrbital.homoLumoNumbersFromJson(test)

        self.assertEqual(homoNum, exp_homoNum)
        self.assertEqual(lumoNum, exp_lumoNum)

        test = {
            "24": {"occupied": True},
            "atomic_coords": [1,2,3],
            "56": {"occupied": True}
        }

        exp_homoNum, exp_lumoNum = 56,False

        homoNum, lumoNum = MolecularOrbital.homoLumoNumbersFromJson(test)

        self.assertEqual(homoNum, exp_homoNum)
        self.assertEqual(lumoNum, exp_lumoNum)
        
    def test_calc_atomic_weight(self):
        """
        Sum the weights on every atom and check it equals eigenvalue of MO.
            - This won't ever be correct. The sum should be 1.
        """
        import os
        testFile = os.path.join(
            os.path.dirname(__file__), "anthracene_output.json"
        )
        for mo_number in [31,32,33,34,35]:
            mo = MolecularOrbital.fromJsonFile(testFile, mo_number)
            mo_eigenvalue = mo.mo["eigenvalue"]
            # sum all atomic weights
            calculated = sum(
                (mo.calc_atomic_weight(x) for x in mo.mo["atomic_contributions"].values())
            )

            self.assertEqual(mo_eigenvalue, calculated,
                msg=f"calculated = {calculated} , mo_eigenvalue = {mo_eigenvalue}"
            )




        

if __name__ == '__main__':
    unittest.main()