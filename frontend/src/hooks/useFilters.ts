import { useState, useEffect } from 'react';
import type { Filters, SectionInfo } from '../types';
import { fetchSections } from '../services/api';

export function useFilters() {
  const [filters, setFilters] = useState<Filters>({ years: [], sections: [] });
  const [availableYears, setAvailableYears] = useState<number[]>([]);
  const [availableSections, setAvailableSections] = useState<SectionInfo[]>([]);

  useEffect(() => {
    fetchSections()
      .then(data => {
        setAvailableYears(data.years || []);
        setAvailableSections(data.sections || []);
      })
      .catch(() => {
        setAvailableYears([2020, 2021, 2022, 2023, 2024, 2025]);
      });
  }, []);

  const toggleYear = (year: number) => {
    setFilters(prev => ({
      ...prev,
      years: prev.years.includes(year)
        ? prev.years.filter(y => y !== year)
        : [...prev.years, year].sort(),
    }));
  };

  const toggleSection = (category: string) => {
    setFilters(prev => ({
      ...prev,
      sections: prev.sections.includes(category)
        ? prev.sections.filter(s => s !== category)
        : [...prev.sections, category],
    }));
  };

  const clearFilters = () => {
    setFilters({ years: [], sections: [] });
  };

  return {
    filters,
    availableYears,
    availableSections,
    toggleYear,
    toggleSection,
    clearFilters,
  };
}
