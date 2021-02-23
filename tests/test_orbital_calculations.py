from typing import List
import unittest

import numpy as np

from y4_python.python_modules.orbital_calculations import PointMass as PM, calc_inertia_tensor, calc_principle_axes


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
            PM(mass=0.25, coords=(0,0,0))
            , PM(mass=0.25, coords=(0,1,0))
            , PM(mass=0.25, coords=(1,0,0))
            , PM(mass=0.25, coords=(1,1,0))
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

if __name__ == '__main__':
    unittest.main()