import { describe, it, expect } from 'vitest';
import { render } from '../test/test-utils';
import { SkeletonTable } from './SkeletonTable';

describe('SkeletonTable', () => {
  it('should render with default props (5 rows, 6 columns)', () => {
    const { container } = render(<SkeletonTable />);
    
    // Count row divs (excluding header)
    const rowDivs = container.querySelectorAll('.px-6.py-4.border-b');
    expect(rowDivs).toHaveLength(5);
  });

  it('should render custom number of rows', () => {
    const { container } = render(<SkeletonTable rows={3} />);
    
    const rowDivs = container.querySelectorAll('.px-6.py-4.border-b');
    expect(rowDivs).toHaveLength(3);
  });

  it('should render custom number of columns', () => {
    const { container } = render(<SkeletonTable columns={4} />);
    
    // Check header columns
    const headerRow = container.querySelector('.bg-gray-50 .flex.gap-6');
    const headerCells = headerRow?.querySelectorAll('.h-4.bg-gray-300');
    expect(headerCells).toHaveLength(4);
  });

  it('should render with both custom rows and columns', () => {
    const { container } = render(<SkeletonTable rows={3} columns={3} />);
    
    const rowDivs = container.querySelectorAll('.px-6.py-4.border-b');
    expect(rowDivs).toHaveLength(3);
    
    const headerRow = container.querySelector('.bg-gray-50 .flex.gap-6');
    const headerCells = headerRow?.querySelectorAll('.h-4.bg-gray-300');
    expect(headerCells).toHaveLength(3);
  });

  it('should have animated skeleton elements', () => {
    const { container } = render(<SkeletonTable />);
    
    const animatedElements = container.querySelectorAll('.animate-pulse');
    expect(animatedElements.length).toBeGreaterThan(0);
  });

  it('should have skeleton placeholders', () => {
    const { container } = render(<SkeletonTable />);
    
    const skeletonBars = container.querySelectorAll('.h-4.bg-gray-200');
    expect(skeletonBars.length).toBeGreaterThan(0);
  });
});
