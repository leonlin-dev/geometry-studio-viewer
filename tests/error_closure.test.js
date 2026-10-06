/**
 * Tests for GeometryParser.parseErrorCodes and
 * GeometryParser.parseClosureSeam (kernel-algo error-code reflection +
 * closed-profile closure-point seam).
 */

import { GeometryParser, MATH_ERROR_TABLE } from '../src/GeometryParser.js';

function assert(cond, msg) { if (!cond) throw new Error(msg || 'assertion failed'); }

const _tests = [
  {
    name: 'parseErrorCodes decorates code with MathError name and meaning',
    fn: async () => {
      const data = { errors: [{ code: 5, message: 'topology mismatch between profiles/guides', context: 'FreeBlend3D' }] };
      const out = GeometryParser.parseErrorCodes(data);
      assert(out.length === 1, 'one record expected');
      assert(out[0].name === 'TOPOLOGY_MISMATCH', 'name should mirror math_error.hpp');
      assert(typeof out[0].meaning === 'string' && out[0].meaning.length > 0, 'meaning text expected');
      assert(out[0].context === 'FreeBlend3D', 'context passthrough');
    }
  },
  {
    name: 'parseErrorCodes returns [] when errors field absent',
    fn: async () => {
      assert(GeometryParser.parseErrorCodes({}).length === 0, 'empty expected');
      assert(GeometryParser.parseErrorCodes({ errors: [] }).length === 0, 'empty expected');
    }
  },
  {
    name: 'parseErrorCodes handles unknown ordinal without throwing',
    fn: async () => {
      const out = GeometryParser.parseErrorCodes({ errors: [{ code: 999 }] });
      assert(out.length === 1 && out[0].name === 'UNKNOWN_ERROR', 'UNKNOWN_ERROR fallback');
    }
  },
  {
    name: 'MATH_ERROR_TABLE covers frozen ordinals 0..23',
    fn: async () => {
      for (let i = 0; i <= 23; i++) {
        assert(MATH_ERROR_TABLE[i], `ordinal ${i} missing`);
      }
      assert(MATH_ERROR_TABLE[5].name === 'TOPOLOGY_MISMATCH', 'ordinal 5 spot-check');
    }
  },
  {
    name: 'parseClosureSeam collects closure points of periodic sections in order',
    fn: async () => {
      const data = {
        curves: [
          { type: 'section', label: 'section_0', is_periodic: true,
            control_points: [[0,0,0],[1,0,0],[0,1,0],[0,0,0]] },
          { type: 'section', label: 'section_1', is_periodic: true,
            control_points: [[0,0,5],[1,0,5],[0,1,5],[0,0,5]] },
          { type: 'spine', control_points: [[0,0,0],[0,0,5]] },
        ]
      };
      const out = GeometryParser.parseClosureSeam(data);
      assert(out.length === 2, 'two closed sections expected');
      assert(out[0].point[0] === 0 && out[0].point[2] === 0, 'first closure point');
      assert(out[1].point[2] === 5, 'second closure point in profile order');
    }
  },
  {
    name: 'parseClosureSeam detects open profiles and skips them',
    fn: async () => {
      const data = {
        curves: [
          { type: 'section', is_periodic: false,
            control_points: [[0,0,0],[1,0,0],[2,1,0]] },
        ]
      };
      assert(GeometryParser.parseClosureSeam(data).length === 0, 'open profile skipped');
    }
  },
  {
    name: 'parseClosureSeam falls back to first≈last CP when is_periodic absent',
    fn: async () => {
      const data = {
        curves: [
          { type: 'section',
            control_points: [[0,0,0],[1,0,0],[0,1,0],[0,0,0]] },
        ]
      };
      const out = GeometryParser.parseClosureSeam(data);
      assert(out.length === 1, 'coincident endpoints detected as closed');
    }
  },
  {
    name: 'parseClosureSeam reads input.profiles when top-level curves absent',
    fn: async () => {
      const data = {
        input: { profiles: [
          { is_periodic: true, control_points: [[1,1,1],[2,1,1],[1,2,1],[1,1,1]] },
        ]}
      };
      const out = GeometryParser.parseClosureSeam(data);
      assert(out.length === 1 && out[0].point[0] === 1, 'input.profiles source');
    }
  },
  {
    name: 'parseClosureSeam returns [] on empty/missing data',
    fn: async () => {
      assert(GeometryParser.parseClosureSeam(null).length === 0, 'null safe');
      assert(GeometryParser.parseClosureSeam({}).length === 0, 'empty safe');
    }
  },
];

export const tests = _tests;
export const description = 'ErrorCodes & ClosureSeam';
